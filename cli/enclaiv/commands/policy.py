"""enclaiv policy — manage network policy presets in enclaiv.yaml."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Manage network policy presets.")
console = Console()

_ENCLAIV_YAML = Path("enclaiv.yaml")

# Policy presets live under templates/policies/ relative to the repo root.
# We walk up from this file to find the repo root (heuristic: look for templates/).
def _find_policies_dir() -> Path:
    candidate = Path(__file__).parent
    for _ in range(6):  # max 6 levels up
        candidate = candidate.parent
        policies = candidate / "templates" / "policies"
        if policies.is_dir():
            return policies
    # Fallback: ~/.enclaiv/policies
    return Path.home() / ".enclaiv" / "policies"


_POLICIES_DIR = _find_policies_dir()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_available_presets() -> list[str]:
    if not _POLICIES_DIR.is_dir():
        return []
    return sorted(p.stem for p in _POLICIES_DIR.glob("*.yaml"))


def _load_preset(name: str) -> dict[str, Any]:
    path = _POLICIES_DIR / f"{name}.yaml"
    if not path.exists():
        available = ", ".join(_list_available_presets()) or "(none found)"
        raise typer.BadParameter(
            f"Preset '{name}' not found in {_POLICIES_DIR}.\n"
            f"Available presets: {available}"
        )
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise typer.BadParameter(f"Policy file '{path}' must be a YAML mapping.")
    return data  # type: ignore[return-value]


def _load_enclaiv_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        console.print(
            f"[red]Error:[/red] '{path}' not found. "
            "Run 'enclaiv init <name>' first."
        )
        raise typer.Exit(code=1)
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        console.print(f"[red]Error:[/red] '{path}' is not a valid YAML mapping.")
        raise typer.Exit(code=1)
    return data  # type: ignore[return-value]


def _save_enclaiv_yaml(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, sort_keys=False)


def _merge_allow_list(existing: list[str], new_entries: list[str]) -> list[str]:
    """Return a deduplicated, order-preserving merged allow list."""
    seen = set(existing)
    merged = list(existing)
    for entry in new_entries:
        if entry not in seen:
            merged.append(entry)
            seen.add(entry)
    return merged


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


@app.command("add")
def policy_add(
    preset: str = typer.Argument(..., help="Preset name (e.g. anthropic, openai, pypi)."),
    config_file: Path = typer.Option(_ENCLAIV_YAML, "--config", "-c"),
) -> None:
    """Merge a policy preset into enclaiv.yaml's network allow list."""
    preset_data = _load_preset(preset)
    enclaiv_data = _load_enclaiv_yaml(config_file)

    new_domains: list[str] = preset_data.get("allow", [])
    if not new_domains:
        console.print(f"[yellow]Warning:[/yellow] Preset '{preset}' has no 'allow' entries.")
        return

    sandbox = enclaiv_data.setdefault("sandbox", {})
    network = sandbox.setdefault("network", {})
    current_allow: list[str] = network.get("allow") or []
    network["allow"] = _merge_allow_list(current_allow, new_domains)

    _save_enclaiv_yaml(config_file, enclaiv_data)

    console.print(
        f"[bold green]Added preset '{preset}'[/bold green] → "
        f"merged {len(new_domains)} domain(s) into {config_file}."
    )
    for d in new_domains:
        console.print(f"  + {d}")


@app.command("remove")
def policy_remove(
    preset: str = typer.Argument(..., help="Preset name to remove."),
    config_file: Path = typer.Option(_ENCLAIV_YAML, "--config", "-c"),
) -> None:
    """Remove a preset's domains from enclaiv.yaml's network allow list."""
    preset_data = _load_preset(preset)
    enclaiv_data = _load_enclaiv_yaml(config_file)

    domains_to_remove: set[str] = set(preset_data.get("allow", []))
    if not domains_to_remove:
        console.print(f"[yellow]Warning:[/yellow] Preset '{preset}' has no 'allow' entries.")
        return

    sandbox = enclaiv_data.get("sandbox", {})
    network = sandbox.get("network", {})
    current_allow: list[str] = network.get("allow") or []

    updated = [d for d in current_allow if d not in domains_to_remove]
    removed_count = len(current_allow) - len(updated)

    network["allow"] = updated
    _save_enclaiv_yaml(config_file, enclaiv_data)

    if removed_count:
        console.print(
            f"[bold yellow]Removed preset '{preset}'[/bold yellow] → "
            f"{removed_count} domain(s) removed from {config_file}."
        )
    else:
        console.print(
            f"[dim]No domains from preset '{preset}' were present in {config_file}.[/dim]"
        )


@app.command("show")
def policy_show(
    config_file: Path = typer.Option(_ENCLAIV_YAML, "--config", "-c"),
) -> None:
    """Display the current network policy from enclaiv.yaml."""
    enclaiv_data = _load_enclaiv_yaml(config_file)
    sandbox = enclaiv_data.get("sandbox", {})
    network = sandbox.get("network", {})
    allow: list[str] = network.get("allow") or []
    deny: list[str] = network.get("deny") or []

    table = Table(title=f"Network Policy — {config_file}", show_lines=False)
    table.add_column("Rule", width=8)
    table.add_column("Domain")

    for d in allow:
        table.add_row("[green]ALLOW[/green]", d)
    for d in deny:
        table.add_row("[red]DENY[/red]", d)
    if not allow and not deny:
        table.add_row("[dim]—[/dim]", "[dim](no rules defined — all traffic blocked)[/dim]")

    console.print(table)

    available = _list_available_presets()
    if available:
        console.print(
            f"\n[dim]Available presets: {', '.join(available)}[/dim]\n"
            "[dim]Add one: enclaiv policy add <preset>[/dim]"
        )


@app.command("list")
def policy_list() -> None:
    """List all available policy presets."""
    presets = _list_available_presets()
    if not presets:
        console.print(
            f"[yellow]No presets found[/yellow] in {_POLICIES_DIR}.\n"
            "Add YAML files to that directory to create presets."
        )
        return

    table = Table(title="Available Policy Presets", show_lines=False)
    table.add_column("Preset", style="cyan")
    table.add_column("Domains")

    for name in presets:
        try:
            data = _load_preset(name)
            domains = ", ".join(data.get("allow", []))
        except Exception:  # noqa: BLE001
            domains = "(error reading preset)"
        table.add_row(name, domains)

    console.print(table)

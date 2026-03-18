"""enclaiv doctor — check that all dependencies are installed and working."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Check CLI dependencies and environment.")
console = Console()


# ---------------------------------------------------------------------------
# Check dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_binary_version(name: str, args: list[str], human_name: str) -> CheckResult:
    """Check that a binary exists and run it to get a version string."""
    binary = shutil.which(name)
    if binary is None:
        return CheckResult(name=human_name, ok=False, detail="not found in PATH")
    try:
        result = subprocess.run(
            [binary, *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_line = (result.stdout or result.stderr).splitlines()[0].strip()
        return CheckResult(name=human_name, ok=True, detail=version_line)
    except (subprocess.TimeoutExpired, OSError, IndexError):
        return CheckResult(name=human_name, ok=True, detail="(version unknown)")


def _check_kraft() -> CheckResult:
    return _check_binary_version("kraft", ["version"], "kraft CLI")


def _check_docker() -> CheckResult:
    return _check_binary_version("docker", ["--version"], "Docker")


def _check_go() -> CheckResult:
    return _check_binary_version("go", ["version"], "Go")


def _check_qemu() -> CheckResult:
    return _check_binary_version("qemu-system-x86_64", ["--version"], "QEMU")


def _check_kvm() -> CheckResult:
    if platform.system() == "Darwin":
        return CheckResult(
            name="KVM (/dev/kvm)",
            ok=True,
            detail="macOS — using QEMU emulation (no hardware isolation; use Linux for KVM)",
        )
    kvm_path = Path("/dev/kvm")
    if kvm_path.exists():
        return CheckResult(
            name="KVM (/dev/kvm)",
            ok=True,
            detail=f"available ({kvm_path})",
        )
    return CheckResult(
        name="KVM (/dev/kvm)",
        ok=False,
        detail=(
            "/dev/kvm not found — hardware isolation unavailable. "
            "Enable nested virtualisation on your host, or use a KVM-capable Linux VM."
        ),
    )


def _check_anthropic_key() -> CheckResult:
    value = os.environ.get("ANTHROPIC_API_KEY")
    if value:
        masked = value[:8] + "…" if len(value) > 8 else "***"
        return CheckResult(name="ANTHROPIC_API_KEY", ok=True, detail=f"set ({masked})")
    return CheckResult(name="ANTHROPIC_API_KEY", ok=False, detail="not set in environment")


def _check_network_proxy_bin() -> CheckResult:
    binary = os.environ.get("ENCLAIV_PROXY_BIN", "enclaiv-proxy")
    path = shutil.which(binary)
    if path:
        return CheckResult(name="Network proxy binary", ok=True, detail=path)
    return CheckResult(
        name="Network proxy binary",
        ok=False,
        detail=(
            f"'{binary}' not found — run 'enclaiv setup' or build the proxy from source "
            "(proxy/ directory). Set ENCLAIV_PROXY_BIN to override."
        ),
    )


def _check_cred_proxy_bin() -> CheckResult:
    binary = os.environ.get("ENCLAIV_CRED_PROXY_BIN", "enclaiv-cred-proxy")
    path = shutil.which(binary)
    if path:
        return CheckResult(name="Credential proxy binary", ok=True, detail=path)
    return CheckResult(
        name="Credential proxy binary",
        ok=False,
        detail=(
            f"'{binary}' not found — run 'enclaiv setup' or build the proxy from source. "
            "Set ENCLAIV_CRED_PROXY_BIN to override."
        ),
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_results(results: list[CheckResult]) -> None:
    table = Table(show_header=True, header_style="bold", show_lines=False)
    table.add_column("Check", width=28)
    table.add_column("Status", width=8)
    table.add_column("Detail")

    ok_count = 0
    for r in results:
        status = "[bold green]✓[/bold green]" if r.ok else "[bold red]✗[/bold red]"
        detail_style = "" if r.ok else "red"
        table.add_row(r.name, status, f"[{detail_style}]{r.detail}[/{detail_style}]" if not r.ok else r.detail)
        if r.ok:
            ok_count += 1

    console.print(table)
    total = len(results)
    if ok_count == total:
        console.print(f"\n[bold green]All {total} checks passed.[/bold green]")
    else:
        failed = total - ok_count
        console.print(
            f"\n[bold red]{failed} check(s) failed.[/bold red] "
            "Resolve the issues above before running 'enclaiv run'."
        )


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def doctor() -> None:
    """Check all Enclaiv dependencies and report their status."""
    console.print("[bold]Running Enclaiv dependency checks…[/bold]\n")

    checks: list[CheckResult] = [
        _check_kraft(),
        _check_kvm(),
        _check_docker(),
        _check_go(),
        _check_qemu(),
        _check_network_proxy_bin(),
        _check_cred_proxy_bin(),
        _check_anthropic_key(),
    ]

    _render_results(checks)

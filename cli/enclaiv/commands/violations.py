"""enclaiv violations [agent-name] — query the proxy's violation store."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from enclaiv.proxy_manager import VIOLATIONS_BASE_URL

app = typer.Typer(help="Show network violations logged by the proxy.")
console = Console()

_VIOLATIONS_ENDPOINT = f"{VIOLATIONS_BASE_URL}/violations"
_REQUEST_TIMEOUT = 5.0  # seconds


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _fetch_violations(agent: Optional[str], session: Optional[str]) -> list[dict[str, Any]]:
    """GET /violations from the running proxy.

    Args:
        agent: Optional agent name filter.
        session: Optional session ID filter.

    Returns:
        List of violation dicts.

    Raises:
        httpx.HTTPError: on network or HTTP errors.
    """
    params: dict[str, str] = {}
    if agent:
        params["agent"] = agent
    if session:
        params["session"] = session

    with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
        response = client.get(_VIOLATIONS_ENDPOINT, params=params)
        response.raise_for_status()
        data = response.json()

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "violations" in data:
        return data["violations"]  # type: ignore[return-value]
    return []


def _format_timestamp(raw: str) -> str:
    """Format an ISO-8601 timestamp as HH:MM:SS for display."""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except (ValueError, AttributeError):
        return raw


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_violations_table(violations: list[dict[str, Any]]) -> None:
    table = Table(
        title=f"Network Violations ({len(violations)} total)",
        show_lines=False,
        header_style="bold magenta",
    )
    table.add_column("Time", style="dim", width=10)
    table.add_column("Status", width=8)
    table.add_column("Destination", style="cyan")
    table.add_column("Agent", style="dim")
    table.add_column("Reason")

    for v in violations:
        table.add_row(
            _format_timestamp(v.get("timestamp", "")),
            "[red]BLOCKED[/red]",
            v.get("destination", "—"),
            v.get("agent_id", "—"),
            v.get("reason", "not in allowlist"),
        )

    console.print(table)


def _render_no_violations() -> None:
    console.print(
        "[bold green]No violations recorded.[/bold green] "
        "The agent stayed within its declared network policy."
    )


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def violations(
    agent: Optional[str] = typer.Argument(
        None,
        help="Filter by agent name (leave blank for all agents).",
    ),
    session: Optional[str] = typer.Option(
        None,
        "--session",
        "-s",
        help="Filter by session ID.",
    ),
    proxy_url: Optional[str] = typer.Option(
        None,
        "--proxy-url",
        help=f"Proxy base URL (default: {VIOLATIONS_BASE_URL}).",
    ),
) -> None:
    """Query the network proxy's violation log.

    Requires the Enclaiv proxy to be running (started by 'enclaiv run').
    """
    global _VIOLATIONS_ENDPOINT  # noqa: PLW0603
    if proxy_url:
        _VIOLATIONS_ENDPOINT = f"{proxy_url.rstrip('/')}/violations"

    try:
        data = _fetch_violations(agent=agent, session=session)
    except httpx.ConnectError:
        console.print(
            "[red]Error:[/red] Could not connect to the Enclaiv proxy at "
            f"{_VIOLATIONS_ENDPOINT}.\n"
            "Is the proxy running? Start it with 'enclaiv run'."
        )
        raise typer.Exit(code=1)
    except httpx.HTTPStatusError as exc:
        console.print(
            f"[red]Error:[/red] Proxy returned HTTP {exc.response.status_code}."
        )
        raise typer.Exit(code=1) from exc
    except httpx.TimeoutException:
        console.print(
            f"[red]Error:[/red] Request to proxy timed out after {_REQUEST_TIMEOUT}s."
        )
        raise typer.Exit(code=1)

    if not data:
        _render_no_violations()
    else:
        _render_violations_table(data)

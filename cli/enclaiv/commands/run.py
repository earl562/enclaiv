"""enclaiv run <task> — build and run the agent in a Unikraft VM (or Docker)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from enclaiv.config import ConfigError, EnclaivConfig, load_config
from enclaiv.kraftfile import generate_kraftfile
from enclaiv.proxy_manager import (
    ProxyError,
    ProxyManager,
    resolve_credentials,
)

app = typer.Typer(help="Run an agent in a sandboxed VM.")
console = Console()

_ENCLAIV_YAML = Path("enclaiv.yaml")

# ---------------------------------------------------------------------------
# Docker fallback helpers
# ---------------------------------------------------------------------------


def _run_docker_fallback(config: EnclaivConfig, task: str, manager: ProxyManager) -> int:
    """Run the agent in a Docker container (--local mode)."""
    image_tag = f"enclaiv-{config.name}:local"

    console.print("[bold]Building Docker image…[/bold]")
    build_result = subprocess.run(
        ["docker", "build", "-t", image_tag, "."],
        check=False,
    )
    if build_result.returncode != 0:
        console.print("[red]Docker build failed.[/red]")
        return build_result.returncode

    env_args: list[str] = []
    for cred in config.credentials:
        if cred.source == "env":
            value = os.environ.get(cred.name, "")
            env_args += ["-e", f"{cred.name}={value}"]

    proxy_env = [
        "-e", f"HTTP_PROXY=http://host.docker.internal:{9080}",
        "-e", f"HTTPS_PROXY=http://host.docker.internal:{9080}",
        "-e", f"ENCLAIV_TASK={task}",
    ]

    console.print("[bold]Running agent in Docker…[/bold]")
    run_result = subprocess.run(
        ["docker", "run", "--rm", *proxy_env, *env_args, image_tag],
        check=False,
    )
    return run_result.returncode


# ---------------------------------------------------------------------------
# Kraft helpers
# ---------------------------------------------------------------------------


def _require_kraft() -> str:
    binary = shutil.which("kraft")
    if binary is None:
        console.print(
            "[red]Error:[/red] 'kraft' not found in PATH.\n"
            "Install it: curl --proto '=https' --tlsv1.2 -sSf https://get.kraftkit.sh | sh\n"
            "Then run 'enclaiv doctor' to verify."
        )
        raise typer.Exit(code=1)
    return binary


def _run_kraft_build(kraft: str, config: EnclaivConfig) -> int:
    console.print("[bold]Building unikernel image…[/bold]")
    result = subprocess.run(
        [kraft, "build", "--arch", "x86_64", "--plat", "qemu"],
        check=False,
    )
    if result.returncode != 0:
        console.print(
            "[red]kraft build failed.[/red] "
            "Check Dockerfile and Kraftfile for errors."
        )
    return result.returncode


def _run_kraft_run(kraft: str, config: EnclaivConfig, task: str) -> int:
    memory_flag = f"{config.sandbox.resources.memory_mib}Mi"
    host_ip = _detect_host_ip()
    proxy_env = (
        f"HTTP_PROXY=http://{host_ip}:9080,"
        f"HTTPS_PROXY=http://{host_ip}:9080,"
        f"ENCLAIV_TASK={task}"
    )
    console.print(
        f"[bold]Booting unikernel VM[/bold] "
        f"(memory={memory_flag}, proxy={host_ip}:9080)…"
    )
    result = subprocess.run(
        [
            kraft,
            "run",
            "--arch", "x86_64",
            "--plat", "qemu",
            "--memory", memory_flag,
            "--env", proxy_env,
        ],
        check=False,
    )
    return result.returncode


def _detect_host_ip() -> str:
    """Return the host IP visible from inside the QEMU guest.

    On macOS/QEMU, this is always 10.0.2.2 (QEMU default gateway).
    On Linux/KVM, it is the KVM bridge IP (typically 192.168.122.1).
    """
    if sys.platform == "darwin":
        return "10.0.2.2"
    # Linux — check for KVM bridge
    kvm_bridge = Path("/sys/class/net/virbr0/address")
    if kvm_bridge.exists():
        return "192.168.122.1"
    return "10.0.2.2"


# ---------------------------------------------------------------------------
# Context manager for proxy lifecycle
# ---------------------------------------------------------------------------


@contextmanager
def _managed_proxies(
    config: EnclaivConfig,
    skip: bool = False,
) -> Generator[Optional[ProxyManager], None, None]:
    """Start proxies before the block, stop them after (even on error)."""
    if skip:
        yield None
        return

    creds = resolve_credentials(config.credentials)
    manager = ProxyManager(
        allowed_domains=config.sandbox.network.allow,
        denied_domains=config.sandbox.network.deny,
        credentials=creds,
    )
    try:
        manager.start_network_proxy()
        manager.start_cred_proxy()
        yield manager
    finally:
        manager.stop_all()


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def run(
    task: str = typer.Argument(..., help="The task description passed to the agent."),
    config_file: Path = typer.Option(
        _ENCLAIV_YAML,
        "--config",
        "-c",
        help="Path to enclaiv.yaml.",
    ),
    local: bool = typer.Option(
        False,
        "--local",
        help="Use Docker instead of a Unikraft VM (faster iteration, less isolation).",
    ),
    no_proxy: bool = typer.Option(
        False,
        "--no-proxy",
        help="Skip proxy startup (useful when running proxies externally).",
    ),
) -> None:
    """Build and run the agent described in enclaiv.yaml.

    The agent executes inside a Unikraft unikernel VM with network
    filtering and credential injection. Use --local for Docker fallback.
    """
    # 1. Load and validate config
    try:
        config = load_config(config_file)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ConfigError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        Panel.fit(
            f"[bold]Agent:[/bold]   {config.name}\n"
            f"[bold]Runtime:[/bold] {config.runtime}\n"
            f"[bold]Mode:[/bold]    {'Docker (--local)' if local else 'Unikraft VM'}\n"
            f"[bold]Task:[/bold]    {task}",
            title="[bold]enclaiv run[/bold]",
            border_style="cyan",
        )
    )

    # 2. Generate Kraftfile (always, even in local mode — useful for debugging)
    try:
        kf_path = generate_kraftfile(config, Path.cwd())
        console.print(f"[dim]Kraftfile written to {kf_path}[/dim]")
    except OSError as exc:
        console.print(f"[red]Error writing Kraftfile:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    # 3. Start proxies and run
    exit_code = 0
    try:
        with _managed_proxies(config, skip=no_proxy or local) as manager:
            if local:
                if manager is None:
                    tmp_manager = ProxyManager(
                        allowed_domains=config.sandbox.network.allow,
                        denied_domains=config.sandbox.network.deny,
                        credentials=resolve_credentials(config.credentials),
                    )
                else:
                    tmp_manager = manager
                exit_code = _run_docker_fallback(config, task, tmp_manager)
            else:
                kraft = _require_kraft()
                rc = _run_kraft_build(kraft, config)
                if rc != 0:
                    raise typer.Exit(code=rc)
                exit_code = _run_kraft_run(kraft, config, task)
    except ProxyError as exc:
        console.print(f"[red]Proxy error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    # 4. Results summary
    if exit_code == 0:
        console.print("\n[bold green]Agent completed successfully.[/bold green]")
        console.print(
            "[dim]Run 'enclaiv violations' to review any blocked network requests.[/dim]"
        )
    else:
        console.print(f"\n[bold red]Agent exited with code {exit_code}.[/bold red]")

    raise typer.Exit(code=exit_code)

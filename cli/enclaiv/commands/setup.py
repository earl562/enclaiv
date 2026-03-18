"""enclaiv setup — first-time environment setup guide."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="First-time environment setup.")
console = Console()


def _is_mac() -> bool:
    return platform.system() == "Darwin"


def _brew_installed() -> bool:
    return shutil.which("brew") is not None


def _run_command(cmd: list[str], description: str) -> bool:
    """Run a shell command, streaming output. Returns True on success."""
    console.print(f"[bold]{description}[/bold]")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        console.print(f"[red]Failed:[/red] {' '.join(cmd)}")
        return False
    return True


def _print_manual_step(step: str, commands: list[str]) -> None:
    cmd_text = "\n".join(f"  [cyan]{c}[/cyan]" for c in commands)
    console.print(f"\n[bold]{step}[/bold]\n{cmd_text}")


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def setup(
    auto_install: bool = typer.Option(
        False,
        "--auto",
        "-y",
        help="Attempt to install missing dependencies automatically (macOS + Homebrew only).",
    ),
) -> None:
    """Guide through installing Enclaiv dependencies.

    On macOS with Homebrew, use --auto to install missing tools automatically.
    On Linux, manual steps are printed.
    """
    console.print(
        Panel.fit(
            "Enclaiv requires: [bold]Go[/bold], [bold]QEMU[/bold], [bold]kraft[/bold], "
            "and [bold]Docker[/bold].\n"
            "Run [cyan]enclaiv doctor[/cyan] after setup to verify everything is working.",
            title="[bold]enclaiv setup[/bold]",
            border_style="cyan",
        )
    )

    if _is_mac():
        _setup_macos(auto_install)
    else:
        _setup_linux()


def _setup_macos(auto_install: bool) -> None:
    if not _brew_installed():
        console.print(
            "[yellow]Homebrew not found.[/yellow] Install it first:\n"
            "  [cyan]/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/"
            "Homebrew/install/HEAD/install.sh)\"[/cyan]"
        )
        return

    tools = [
        ("go", ["brew", "install", "go"]),
        ("qemu-system-x86_64", ["brew", "install", "qemu"]),
        ("docker", ["brew", "install", "--cask", "docker"]),
    ]

    for binary, install_cmd in tools:
        if shutil.which(binary):
            console.print(f"[green]✓[/green] {binary} already installed")
        elif auto_install:
            _run_command(install_cmd, f"Installing {binary}…")
        else:
            console.print(
                f"[yellow]✗[/yellow] {binary} missing. Install with:\n"
                f"  [cyan]{' '.join(install_cmd)}[/cyan]"
            )

    # kraft has its own installer script
    if shutil.which("kraft"):
        console.print("[green]✓[/green] kraft already installed")
    elif auto_install:
        _run_command(
            [
                "sh", "-c",
                "curl --proto '=https' --tlsv1.2 -sSf https://get.kraftkit.sh | sh",
            ],
            "Installing kraft CLI…",
        )
    else:
        _print_manual_step(
            "Install kraft CLI:",
            ["curl --proto '=https' --tlsv1.2 -sSf https://get.kraftkit.sh | sh"],
        )

    console.print(
        "\n[bold]Proxy binaries:[/bold] Build them from the [cyan]proxy/[/cyan] directory:\n"
        "  [cyan]cd proxy && go build -o enclaiv-proxy ./cmd/proxy[/cyan]\n"
        "  [cyan]go build -o enclaiv-cred-proxy ./cmd/cred-proxy[/cyan]\n"
        "  [cyan]sudo mv enclaiv-proxy enclaiv-cred-proxy /usr/local/bin/[/cyan]"
    )

    console.print(
        "\nRun [cyan]enclaiv doctor[/cyan] to verify your setup."
    )


def _setup_linux() -> None:
    _print_manual_step(
        "1. Install Go:",
        ["sudo apt update && sudo apt install -y golang-go"],
    )
    _print_manual_step(
        "2. Install QEMU:",
        ["sudo apt install -y qemu-system-x86"],
    )
    _print_manual_step(
        "3. Install Docker:",
        [
            "sudo apt install -y docker.io",
            "sudo usermod -aG docker $USER",
            "newgrp docker",
        ],
    )
    _print_manual_step(
        "4. Install kraft CLI:",
        ["curl --proto '=https' --tlsv1.2 -sSf https://get.kraftkit.sh | sh"],
    )
    _print_manual_step(
        "5. Build proxy binaries (from repo root):",
        [
            "cd proxy && go build -o enclaiv-proxy ./cmd/proxy",
            "go build -o enclaiv-cred-proxy ./cmd/cred-proxy",
            "sudo mv enclaiv-proxy enclaiv-cred-proxy /usr/local/bin/",
        ],
    )
    _print_manual_step(
        "6. Verify KVM is available (Linux with nested virtualisation):",
        ["ls -la /dev/kvm"],
    )
    console.print("\nRun [cyan]enclaiv doctor[/cyan] to verify your setup.")

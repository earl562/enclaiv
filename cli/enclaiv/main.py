"""Enclaiv CLI — entry point and top-level Typer app."""

import typer
from rich.console import Console

from enclaiv import __version__
from enclaiv.commands.init_cmd import app as init_app
from enclaiv.commands.run import app as run_app
from enclaiv.commands.violations import app as violations_app
from enclaiv.commands.doctor import app as doctor_app
from enclaiv.commands.policy import app as policy_app
from enclaiv.commands.setup import app as setup_app

app = typer.Typer(
    name="enclaiv",
    help="Run AI agents in hardware-isolated Unikraft unikernel VMs.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()

app.add_typer(init_app, name="init")
app.add_typer(run_app, name="run")
app.add_typer(violations_app, name="violations")
app.add_typer(doctor_app, name="doctor")
app.add_typer(policy_app, name="policy")
app.add_typer(setup_app, name="setup")


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold green]enclaiv[/bold green] version [cyan]{__version__}[/cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the current version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """[bold]Enclaiv[/bold] — Run AI agents in hardware-isolated Unikraft unikernel VMs.

    Every agent runs in its own VM with declared-upfront network access,
    no raw credentials, and full violation tracking.
    """


if __name__ == "__main__":
    app()

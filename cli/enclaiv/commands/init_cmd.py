"""enclaiv init <name> — scaffold a new agent project directory."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="Scaffold a new agent project.")
console = Console()

# Path to the bundled python-basic template (relative to this file).
_TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "templates" / "python-basic"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise typer.BadParameter("Agent name must not be empty.")
    if not all(c.isalnum() or c in "-_" for c in name):
        raise typer.BadParameter(
            f"Invalid agent name '{name}'. "
            "Use only letters, digits, hyphens, and underscores."
        )
    return name


def _render_enclaiv_yaml(name: str) -> str:
    return f"""\
name: {name}
runtime: python:3.11
sandbox:
  network:
    allow:
      - api.anthropic.com
    deny: []
  filesystem:
    writable:
      - ./output
      - /tmp
    deny_read:
      - ~/.ssh
      - ~/.aws
      - .env
  resources:
    memory: 512mb
    cpu: 1
    timeout: 300s
credentials:
  - name: ANTHROPIC_API_KEY
    source: env
"""


def _render_dockerfile() -> str:
    return """\
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py .

CMD ["python3", "/app/agent.py"]
"""


def _render_agent_py(name: str) -> str:
    return f'''\
"""
{name} — Enclaiv agent entry point.

This script runs inside a hardware-isolated Unikraft unikernel VM.
Network access is limited to the domains declared in enclaiv.yaml.
API keys are never present in this environment — they are injected
transparently by the Enclaiv credential proxy.
"""

import anthropic


def main() -> None:
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            {{"role": "user", "content": "Hello! What can you do for me today?"}}
        ],
    )

    print(message.content[0].text)


if __name__ == "__main__":
    main()
'''


def _render_requirements() -> str:
    return "anthropic>=0.28\n"


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def init(
    name: str = typer.Argument(..., help="Name for the new agent project."),
    template: str = typer.Option(
        "python-basic",
        "--template",
        "-t",
        help="Starter template to use.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite an existing directory.",
    ),
) -> None:
    """Scaffold a new Enclaiv agent project in a subdirectory called <name>."""

    name = _validate_name(name)
    project_dir = Path.cwd() / name

    if project_dir.exists() and not force:
        console.print(
            f"[red]Error:[/red] Directory '{project_dir}' already exists. "
            "Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    if project_dir.exists() and force:
        shutil.rmtree(project_dir)

    project_dir.mkdir(parents=True)
    (project_dir / "output").mkdir()

    # Write files
    (project_dir / "enclaiv.yaml").write_text(_render_enclaiv_yaml(name), encoding="utf-8")
    (project_dir / "Dockerfile").write_text(_render_dockerfile(), encoding="utf-8")
    (project_dir / "agent.py").write_text(_render_agent_py(name), encoding="utf-8")
    (project_dir / "requirements.txt").write_text(_render_requirements(), encoding="utf-8")

    console.print(
        Panel.fit(
            f"[bold green]Created agent project:[/bold green] {project_dir}\n\n"
            "[dim]Files created:[/dim]\n"
            "  enclaiv.yaml   — sandbox policy\n"
            "  agent.py       — agent entry point\n"
            "  Dockerfile     — VM root filesystem\n"
            "  requirements.txt\n"
            "  output/        — writable output directory\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  [cyan]cd {name}[/cyan]\n"
            "  [cyan]enclaiv doctor[/cyan]       — verify dependencies\n"
            "  [cyan]enclaiv run \"your task\"[/cyan]",
            title="[bold]enclaiv init[/bold]",
            border_style="green",
        )
    )

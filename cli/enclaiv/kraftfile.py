"""Generate a Kraftfile (v0.6) from a parsed EnclaivConfig."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from enclaiv.config import EnclaivConfig

# ---------------------------------------------------------------------------
# Kraftfile generation
# ---------------------------------------------------------------------------

KRAFTFILE_SPEC = "v0.6"


def _runtime_to_cmd(runtime: str) -> list[str]:
    """Derive a sensible default CMD from the runtime string."""
    lang = runtime.split(":")[0].lower()
    if lang == "python":
        return ["/usr/bin/python3", "/app/agent.py"]
    if lang == "node":
        return ["/usr/bin/node", "/app/agent.js"]
    if lang == "go":
        return ["/app/agent"]
    if lang == "rust":
        return ["/app/agent"]
    return ["/app/agent"]


def build_kraftfile_dict(config: EnclaivConfig) -> dict[str, Any]:
    """Return the Kraftfile content as a Python dict."""
    return {
        "spec": KRAFTFILE_SPEC,
        "runtime": config.runtime,
        "rootfs": "./Dockerfile",
        "cmd": _runtime_to_cmd(config.runtime),
    }


def generate_kraftfile(config: EnclaivConfig, output_dir: Path) -> Path:
    """Write a Kraftfile to *output_dir* and return the path.

    The file is always named ``Kraftfile`` (no extension), which is what
    ``kraft build`` expects by default.

    Args:
        config: Parsed and validated EnclaivConfig.
        output_dir: Directory where the Kraftfile will be written.

    Returns:
        Path to the written Kraftfile.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    kraftfile_path = output_dir / "Kraftfile"

    content = build_kraftfile_dict(config)
    with kraftfile_path.open("w", encoding="utf-8") as fh:
        yaml.dump(content, fh, default_flow_style=False, sort_keys=False)

    return kraftfile_path


def kraftfile_as_string(config: EnclaivConfig) -> str:
    """Return the Kraftfile as a YAML string (for display or testing)."""
    content = build_kraftfile_dict(config)
    return yaml.dump(content, default_flow_style=False, sort_keys=False)

"""Parse and validate enclaiv.yaml into frozen dataclasses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Dataclasses (all frozen — immutable after creation)
# ---------------------------------------------------------------------------

MEMORY_PATTERN = re.compile(r"^(\d+)(mb|gb|Mi|Gi)$", re.IGNORECASE)
TIMEOUT_PATTERN = re.compile(r"^(\d+)(s|m|h)$", re.IGNORECASE)


@dataclass(frozen=True)
class NetworkConfig:
    allow: tuple[str, ...] = field(default_factory=tuple)
    deny: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FilesystemConfig:
    writable: tuple[str, ...] = field(default_factory=tuple)
    deny_read: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResourcesConfig:
    memory: str = "512mb"
    cpu: int = 1
    timeout: str = "300s"

    @property
    def memory_mib(self) -> int:
        """Return memory as an integer MiB value for kraft."""
        m = MEMORY_PATTERN.match(self.memory)
        if not m:
            return 512
        value, unit = int(m.group(1)), m.group(2).lower()
        if unit in ("gb", "gi"):
            return value * 1024
        return value

    @property
    def timeout_seconds(self) -> int:
        """Return timeout as integer seconds."""
        m = TIMEOUT_PATTERN.match(self.timeout)
        if not m:
            return 300
        value, unit = int(m.group(1)), m.group(2).lower()
        if unit == "m":
            return value * 60
        if unit == "h":
            return value * 3600
        return value


@dataclass(frozen=True)
class SandboxConfig:
    network: NetworkConfig = field(default_factory=NetworkConfig)
    filesystem: FilesystemConfig = field(default_factory=FilesystemConfig)
    resources: ResourcesConfig = field(default_factory=ResourcesConfig)


@dataclass(frozen=True)
class CredentialConfig:
    name: str
    source: str  # "env" | "file" | "vault"


@dataclass(frozen=True)
class EnclaivConfig:
    name: str
    runtime: str
    sandbox: SandboxConfig
    credentials: tuple[CredentialConfig, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_network(raw: dict[str, Any]) -> NetworkConfig:
    return NetworkConfig(
        allow=tuple(raw.get("allow") or []),
        deny=tuple(raw.get("deny") or []),
    )


def _parse_filesystem(raw: dict[str, Any]) -> FilesystemConfig:
    return FilesystemConfig(
        writable=tuple(raw.get("writable") or []),
        deny_read=tuple(raw.get("deny_read") or []),
    )


def _parse_resources(raw: dict[str, Any]) -> ResourcesConfig:
    memory = str(raw.get("memory", "512mb"))
    cpu = int(raw.get("cpu", 1))
    timeout = str(raw.get("timeout", "300s"))
    _validate_memory(memory)
    _validate_timeout(timeout)
    return ResourcesConfig(memory=memory, cpu=cpu, timeout=timeout)


def _parse_sandbox(raw: dict[str, Any]) -> SandboxConfig:
    network = _parse_network(raw.get("network") or {})
    filesystem = _parse_filesystem(raw.get("filesystem") or {})
    resources = _parse_resources(raw.get("resources") or {})
    return SandboxConfig(network=network, filesystem=filesystem, resources=resources)


def _parse_credentials(raw_list: list[dict[str, Any]]) -> tuple[CredentialConfig, ...]:
    creds: list[CredentialConfig] = []
    for item in raw_list:
        if "name" not in item:
            raise ConfigError("Each credential entry must have a 'name' field.")
        source = item.get("source", "env")
        if source not in ("env", "file", "vault"):
            raise ConfigError(
                f"Credential '{item['name']}' has unknown source '{source}'. "
                "Valid values: env, file, vault."
            )
        creds.append(CredentialConfig(name=str(item["name"]), source=str(source)))
    return tuple(creds)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def _validate_memory(value: str) -> None:
    if not MEMORY_PATTERN.match(value):
        raise ConfigError(
            f"Invalid memory value '{value}'. Examples: 512mb, 2gb, 1Gi."
        )


def _validate_timeout(value: str) -> None:
    if not TIMEOUT_PATTERN.match(value):
        raise ConfigError(
            f"Invalid timeout value '{value}'. Examples: 300s, 5m, 1h."
        )


def _validate_runtime(value: str) -> None:
    known_prefixes = ("python:", "node:", "go:", "rust:")
    if not any(value.startswith(p) for p in known_prefixes):
        console.print(
            f"[yellow]Warning:[/yellow] Runtime '{value}' is not a recognized prefix "
            f"({', '.join(known_prefixes)}). Proceeding anyway."
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Raised when enclaiv.yaml is invalid."""


def load_config(path: Path) -> EnclaivConfig:
    """Read, parse, and validate an enclaiv.yaml file.

    Raises:
        ConfigError: on any validation failure.
        FileNotFoundError: if the path does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"enclaiv.yaml not found at '{path}'. "
            "Run 'enclaiv init <name>' to create a new project."
        )

    raw: Any
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML parse error in '{path}': {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"'{path}' must be a YAML mapping at the top level.")

    name = str(raw.get("name") or "").strip()
    if not name:
        raise ConfigError("enclaiv.yaml must have a non-empty 'name' field.")

    runtime = str(raw.get("runtime") or "").strip()
    if not runtime:
        raise ConfigError("enclaiv.yaml must have a non-empty 'runtime' field.")

    _validate_runtime(runtime)

    sandbox = _parse_sandbox(raw.get("sandbox") or {})
    credentials = _parse_credentials(raw.get("credentials") or [])

    return EnclaivConfig(
        name=name,
        runtime=runtime,
        sandbox=sandbox,
        credentials=credentials,
    )

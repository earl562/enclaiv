"""Start and stop the Go network proxy and credential proxy as subprocesses."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

# Default locations — can be overridden via environment variables.
_DEFAULT_PROXY_BINARY = os.environ.get("ENCLAIV_PROXY_BIN", "enclaiv-proxy")
_DEFAULT_CRED_PROXY_BINARY = os.environ.get("ENCLAIV_CRED_PROXY_BIN", "enclaiv-cred-proxy")

NETWORK_PROXY_PORT = int(os.environ.get("ENCLAIV_PROXY_PORT", "9080"))
VIOLATIONS_PORT = int(os.environ.get("ENCLAIV_VIOLATIONS_PORT", "9081"))
CRED_PROXY_PORT = int(os.environ.get("ENCLAIV_CRED_PROXY_PORT", "9082"))
VIOLATIONS_BASE_URL = f"http://localhost:{VIOLATIONS_PORT}"


@dataclass
class ProxyProcess:
    """Tracks a single running proxy subprocess."""

    name: str
    process: subprocess.Popen  # type: ignore[type-arg]
    port: int

    def is_running(self) -> bool:
        return self.process.poll() is None

    def stop(self, timeout: float = 5.0) -> None:
        """Send SIGTERM, wait *timeout* seconds, then SIGKILL if still alive."""
        if not self.is_running():
            return
        self.process.send_signal(signal.SIGTERM)
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            console.print(
                f"[yellow]Warning:[/yellow] {self.name} did not stop after {timeout}s — sending SIGKILL."
            )
            self.process.kill()
            self.process.wait()

    def returncode(self) -> Optional[int]:
        return self.process.returncode


@dataclass
class ProxyManager:
    """Manages the lifecycle of both proxy processes."""

    allowed_domains: tuple[str, ...]
    denied_domains: tuple[str, ...]
    credentials: dict[str, str] = field(default_factory=dict)
    network_proxy_bin: str = _DEFAULT_PROXY_BINARY
    cred_proxy_bin: str = _DEFAULT_CRED_PROXY_BINARY

    _network_proxy: Optional[ProxyProcess] = field(default=None, init=False, repr=False)
    _cred_proxy: Optional[ProxyProcess] = field(default=None, init=False, repr=False)

    def start_network_proxy(self) -> ProxyProcess:
        """Launch the network (allowlist) proxy."""
        binary = shutil.which(self.network_proxy_bin)
        if binary is None:
            raise ProxyError(
                f"Network proxy binary '{self.network_proxy_bin}' not found in PATH.\n"
                "Run 'enclaiv doctor' to check dependencies, "
                "or set ENCLAIV_PROXY_BIN to the correct path."
            )

        allow_arg = ",".join(self.allowed_domains)
        deny_arg = ",".join(self.denied_domains)
        cmd = [
            binary,
            f"--port={NETWORK_PROXY_PORT}",
            f"--allow={allow_arg}",
            f"--deny={deny_arg}",
        ]

        console.print(
            f"[dim]Starting network proxy on port {NETWORK_PROXY_PORT}…[/dim]"
        )
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _wait_for_port(NETWORK_PROXY_PORT, timeout=10.0, process_name="network proxy")
        self._network_proxy = ProxyProcess(
            name="network-proxy", process=proc, port=NETWORK_PROXY_PORT
        )
        return self._network_proxy

    def start_cred_proxy(self) -> ProxyProcess:
        """Launch the credential-injection proxy."""
        binary = shutil.which(self.cred_proxy_bin)
        if binary is None:
            raise ProxyError(
                f"Credential proxy binary '{self.cred_proxy_bin}' not found in PATH.\n"
                "Run 'enclaiv doctor' to check dependencies, "
                "or set ENCLAIV_CRED_PROXY_BIN to the correct path."
            )

        env = {**os.environ}
        for key, value in self.credentials.items():
            env[key] = value

        cmd = [
            binary,
            f"--port={CRED_PROXY_PORT}",
            f"--upstream-port={NETWORK_PROXY_PORT}",
        ]

        console.print(
            f"[dim]Starting credential proxy on port {CRED_PROXY_PORT}…[/dim]"
        )
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        _wait_for_port(CRED_PROXY_PORT, timeout=10.0, process_name="credential proxy")
        self._cred_proxy = ProxyProcess(
            name="cred-proxy", process=proc, port=CRED_PROXY_PORT
        )
        return self._cred_proxy

    def stop_all(self) -> None:
        """Gracefully stop both proxies."""
        for proxy in (self._cred_proxy, self._network_proxy):
            if proxy is not None:
                console.print(f"[dim]Stopping {proxy.name}…[/dim]")
                proxy.stop()

    @property
    def network_proxy(self) -> Optional[ProxyProcess]:
        return self._network_proxy

    @property
    def cred_proxy(self) -> Optional[ProxyProcess]:
        return self._cred_proxy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_for_port(port: int, timeout: float, process_name: str) -> None:
    """Poll until a TCP port accepts connections or *timeout* elapses."""
    import socket

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise ProxyError(
        f"{process_name} did not start within {timeout:.0f}s "
        f"(port {port} never opened)."
    )


def resolve_credentials(credential_configs: tuple) -> dict[str, str]:
    """Read credential values from their declared sources.

    Only 'env' source is supported in this release. 'file' and 'vault'
    are reserved for future phases.

    Returns a dict of {name: value} for credentials that are present.
    Missing env vars are reported as warnings, not errors.
    """
    resolved: dict[str, str] = {}
    for cred in credential_configs:
        if cred.source == "env":
            value = os.environ.get(cred.name)
            if value is None:
                console.print(
                    f"[yellow]Warning:[/yellow] Credential '{cred.name}' "
                    "not found in environment — it will not be injected."
                )
            else:
                resolved[cred.name] = value
        else:
            console.print(
                f"[yellow]Warning:[/yellow] Credential source '{cred.source}' "
                f"for '{cred.name}' is not yet supported — skipping."
            )
    return resolved


class ProxyError(Exception):
    """Raised when a proxy process cannot be started or stopped."""

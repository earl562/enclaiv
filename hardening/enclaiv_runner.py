"""
enclaiv_runner.py — Python wrapper executed inside the Unikraft VM.

Responsibilities:
  1. Read sensitive credentials from the environment.
  2. Immediately strip them from os.environ so child processes cannot inherit
     them via /proc/self/environ or environment inspection.
  3. Enforce proxy settings.
  4. Execute the agent's actual entrypoint via runpy so no new process is
     spawned (keeps the process tree minimal and avoids re-inheriting env).

POSIX guarantee: this script must work with CPython 3.11+ only.
"""

from __future__ import annotations

import os
import runpy
import sys
from dataclasses import dataclass, field
from typing import Final


# ---------------------------------------------------------------------------
# Frozen dataclass — immutable session config consumed once at startup.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SessionConfig:
    session_token: str
    control_plane_url: str
    session_id: str
    agent_module: str
    proxy_url: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SENSITIVE_KEYS: Final[tuple[str, ...]] = (
    "SESSION_TOKEN",
    "CONTROL_PLANE_URL",
    "SESSION_ID",
)

_PROXY_HOST: Final[str] = "10.0.2.2"
_PROXY_PORT: Final[int] = 9080
_DEFAULT_PROXY_URL: Final[str] = f"http://{_PROXY_HOST}:{_PROXY_PORT}"

# The agent module to run, injected by the control plane or defaulting to the
# well-known entry point bundled in the VM image.
_DEFAULT_AGENT_MODULE: Final[str] = "agent.main"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_env(key: str) -> str:
    """Return the value of *key* from the environment or abort with a clear message."""
    value = os.environ.get(key, "")
    if not value:
        print(f"[enclaiv-runner] FATAL: required environment variable '{key}' is not set",
              file=sys.stderr)
        sys.exit(1)
    return value


def _strip_sensitive_env(keys: tuple[str, ...]) -> None:
    """Remove *keys* from os.environ so child processes cannot inherit them."""
    for key in keys:
        if key in os.environ:
            del os.environ[key]
            # Overwrite any lingering trace in the process environment block.
            os.putenv(key, "")  # noqa: S604  (intentional blank override)


def _configure_proxy(proxy_url: str) -> None:
    """Force all HTTP(S) traffic through the allowlist proxy."""
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url
    os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
    os.environ["no_proxy"] = os.environ["NO_PROXY"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_session_config() -> SessionConfig:
    """Read credentials, validate them, and return an immutable config object."""
    session_token = _require_env("SESSION_TOKEN")
    control_plane_url = _require_env("CONTROL_PLANE_URL")
    session_id = _require_env("SESSION_ID")
    agent_module = os.environ.get("AGENT_MODULE", _DEFAULT_AGENT_MODULE)
    proxy_url = os.environ.get("ENCLAIV_PROXY_URL", _DEFAULT_PROXY_URL)

    return SessionConfig(
        session_token=session_token,
        control_plane_url=control_plane_url,
        session_id=session_id,
        agent_module=agent_module,
        proxy_url=proxy_url,
    )


def main() -> None:
    # Step 1 — collect credentials before wiping them from the environment.
    config = build_session_config()

    # Step 2 — wipe sensitive values so no subprocess can read them from env.
    _strip_sensitive_env(_SENSITIVE_KEYS)
    # Also strip the AGENT_MODULE variable; it's baked into config now.
    _strip_sensitive_env(("AGENT_MODULE", "ENCLAIV_PROXY_URL"))

    # Step 3 — (re)enforce proxy after stripping, using the value captured
    # before stripping.
    _configure_proxy(config.proxy_url)

    print(
        f"[enclaiv-runner] Starting agent module '{config.agent_module}' "
        f"for session '{config.session_id}'",
        file=sys.stderr,
    )

    # Step 4 — hand control to the agent.  runpy.run_module executes the
    # module inside this interpreter process, so:
    #   - no new process is forked (no env re-inheritance risk);
    #   - the already-stripped os.environ is the only visible environment.
    try:
        runpy.run_module(config.agent_module, run_name="__main__", alter_sys=True)
    except ImportError as exc:
        print(
            f"[enclaiv-runner] FATAL: could not import agent module "
            f"'{config.agent_module}': {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    except SystemExit:
        # Let the agent's own exit code propagate normally.
        raise
    except Exception as exc:  # noqa: BLE001
        print(
            f"[enclaiv-runner] FATAL: unhandled exception in agent: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

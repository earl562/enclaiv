#!/bin/sh
# Enclaiv VM entrypoint — runs inside the Unikraft VM before the agent.
# POSIX sh compatible (no bash-isms).

set -eu

# ---------------------------------------------------------------------------
# 1. Read credential tokens from the environment (injected by the control plane
#    via the VM's kernel command line or virtio-vsock metadata channel).
# ---------------------------------------------------------------------------
SESSION_TOKEN="${SESSION_TOKEN:-}"
CONTROL_PLANE_URL="${CONTROL_PLANE_URL:-}"
SESSION_ID="${SESSION_ID:-}"

if [ -z "${SESSION_TOKEN}" ]; then
    echo "[enclaiv] ERROR: SESSION_TOKEN is not set" >&2
    exit 1
fi

if [ -z "${CONTROL_PLANE_URL}" ]; then
    echo "[enclaiv] ERROR: CONTROL_PLANE_URL is not set" >&2
    exit 1
fi

if [ -z "${SESSION_ID}" ]; then
    echo "[enclaiv] ERROR: SESSION_ID is not set" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 2. Route all outbound HTTP(S) through the allowlist proxy running on the
#    QEMU host.  10.0.2.2 is the gateway address in QEMU's user-mode network.
# ---------------------------------------------------------------------------
PROXY_HOST="10.0.2.2"
PROXY_PORT="9080"

export HTTP_PROXY="http://${PROXY_HOST}:${PROXY_PORT}"
export HTTPS_PROXY="http://${PROXY_HOST}:${PROXY_PORT}"
export http_proxy="${HTTP_PROXY}"
export https_proxy="${HTTPS_PROXY}"

# Do not proxy localhost / loopback traffic.
export NO_PROXY="localhost,127.0.0.1,::1"
export no_proxy="${NO_PROXY}"

echo "[enclaiv] Proxy set to ${HTTP_PROXY}"

# ---------------------------------------------------------------------------
# 3. Drop privileges.  Switch from root (UID 0) to nobody (UID 65534).
#    We use 'su' rather than 'exec setuid' so the approach works in minimal
#    rootfs images that may not have 'gosu' or 'su-exec'.
# ---------------------------------------------------------------------------
RUNNER_UID=65534
RUNNER_GID=65534

if [ "$(id -u)" -eq 0 ]; then
    echo "[enclaiv] Dropping privileges to UID=${RUNNER_UID} GID=${RUNNER_GID}"

    # Ensure /tmp is writable by nobody before dropping.
    chown "${RUNNER_UID}:${RUNNER_GID}" /tmp 2>/dev/null || true
    chmod 1777 /tmp 2>/dev/null || true

    # Re-exec this script as nobody so the rest of the process tree inherits
    # the reduced UID.  Pass all environment variables explicitly.
    exec su -s /bin/sh -c \
        "exec python3 /opt/enclaiv/enclaiv_runner.py" \
        nobody
else
    echo "[enclaiv] Already running as UID=$(id -u), skipping privilege drop"
fi

# ---------------------------------------------------------------------------
# 4. Execute the agent via the Python runner (reached only when already
#    running as an unprivileged user).
# ---------------------------------------------------------------------------
exec python3 /opt/enclaiv/enclaiv_runner.py

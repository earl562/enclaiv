# Enclaiv — Build Guide

> You are building this yourself. This doc is your map.
> When something doesn't make sense, ask. When you get stuck on code, ask.
> Work through it in order — each phase depends on the last.

---

## What You're Building

An open-source platform that runs every AI agent in its own hardware-isolated virtual machine.

**The security model in one sentence:** The agent has no API keys, no cloud credentials, and no unrestricted network access. Everything it can do is declared upfront in `enclaiv.yaml`.

**The five pieces:**
1. `enclaiv.yaml` — the config file that declares what the agent is allowed to do
2. `enclaiv` CLI (Python) — developer interface: `init`, `run`, `deploy`, `violations`
3. Network Proxy (Go) — every byte the agent sends goes through this; unlisted domains are blocked
4. Control Plane (FastAPI) — auth, session management, LLM proxy (agent never sees API keys)
5. Unikraft VM — hardware-isolated execution environment (KVM, qemu/x86_64)

**MVP = all pieces.** A working agent that runs in a hardware-isolated unikernel VM with network
filtering and credential injection via the control plane.

---

## Current Status (MVP Complete)

| Component | Status | Notes |
|-----------|--------|-------|
| `enclaiv.yaml` parser + CLI | ✅ Complete | `init`, `run`, `doctor`, `violations` |
| Network Proxy (Go) | ✅ Complete | Allowlist, CONNECT handler, violations API |
| Control Plane (FastAPI) | ✅ Complete | Session auth, LLM proxy (Anthropic + Gemini) |
| Docker local mode (`--local`) | ✅ Complete | `enclaiv run --local` for fast iteration |
| Unikraft unikernel build | ✅ Complete | `kraft build` + `kraft run` on GCP KVM |
| End-to-end smoke test | ✅ Complete | Unikernel → control plane → Gemini 2.5 Flash |
| Bytecode hardening | ✅ Complete | `.py` deleted, only `.pyc` in VM rootfs |
| Network filter | ✅ Complete | Allowlist via `proxy/config/allowlist.json`; undeclared domains blocked |
| API key isolation | ✅ Complete | No API key ever enters the VM |

---

## Production Deployment (GCP)

### Stack

The full stack runs on GCP instance `enclaiv-dev` (us-central1-a):

```
docker compose up -d db control-plane proxy
```

- **PostgreSQL** — session store, message history
- **Control plane** — FastAPI, port 8080, uvicorn 2 workers
- **Go proxy** — allowlist proxy port 9080, violations API port 9081
- **kraft0 bridge** — VM networking (172.19.0.1/16)

### Running an agent

```bash
# From the GCP instance
cd ~/enclaiv/test-agent

# Build the unikernel (first time only — subsequent runs use cache)
kraft build --arch x86_64 --plat qemu

# Run (creates session on control plane, boots VM)
sudo -E kraft run \
  --arch x86_64 --plat qemu --memory 512Mi --network kraft0 \
  --env "SESSION_TOKEN=<token>" \
  --env "CONTROL_PLANE_URL=http://172.19.0.1:8080" \
  --env "ENCLAIV_TASK=<task>"

# Or use the CLI (local Docker mode — fast)
export PATH=$PATH:$HOME/.local/bin
enclaiv run --local --no-proxy "your task here"
```

### Known requirements for kraft run on Linux/KVM

1. **KVM group**: `sudo usermod -aG kvm $USER` + new SSH session
2. **CAP_NET_ADMIN on QEMU**: `sudo setcap cap_net_admin=eip $(which qemu-system-x86_64)`
3. **kraft0 bridge**: `sudo kraft net create --driver=bridge kraft0`
4. **iptables FORWARD**: `sudo iptables -I FORWARD 1 -j ACCEPT` (allows kraft0 → Docker)
5. **sudo for kraft run**: `sudo -E kraft run ...` (kraft itself needs CAP_NET_ADMIN to create tap)
6. **Disk space**: Keep >1 GB free — kraft unpacks ~600 MB per run to `/tmp`
7. **KRAFTKIT_NO_WARN_SUDO=1**: Suppress sudo warnings from kraft

### Dockerfile requirements for Unikraft CPIO

The unikernel rootfs is packed as a CPIO archive. Unikraft's CPIO handler does **not** support
hard links. `python:3.12-slim` contains one hard link pair: `/usr/bin/perl` ↔ `/usr/bin/perl5.40.1`.
Break it in the Dockerfile:

```dockerfile
RUN cp --remove-destination /usr/bin/perl /usr/bin/perl5.40.1
```

### Environment variable format for kraft run

Use **separate `--env` flags** for each variable. Do **not** use a single comma-delimited string —
kraft's comma parsing truncates values that contain colons (e.g. URLs):

```bash
# CORRECT
kraft run --env "SESSION_TOKEN=..." --env "CONTROL_PLANE_URL=http://..."

# WRONG — CONTROL_PLANE_URL gets truncated at the colon
kraft run --env "SESSION_TOKEN=...,CONTROL_PLANE_URL=http://..."
```

### Proxy allowlist configuration

The Go proxy reads `proxy/config/allowlist.json` at startup (mounted as `/config/allowlist.json`
in the Docker container). Edit this file to control which domains the agent can reach:

```json
{
  "allowed": ["arxiv.org", "api.anthropic.com", "generativelanguage.googleapis.com"],
  "denied":  ["evil.com"]
}
```

Restart the proxy after editing: `docker compose restart proxy`

The `denied` list takes precedence over `allowed`. An empty `allowed` list means deny-all.

### VPC firewall rules (multi-instance production only)

For a multi-instance deployment where unikernels run on separate GCP VMs:

```bash
# Tag the unikernel instances
gcloud compute instances add-tags <unikernel-vm> --tags=enclaiv-vm

# Block all egress from unikernel instances
gcloud compute firewall-rules create enclaiv-vm-egress-deny \
  --direction=EGRESS --action=DENY --rules=all \
  --target-tags=enclaiv-vm --priority=1000

# Allow unikernel → control plane only
CP_IP=$(gcloud compute instances describe enclaiv-cp-vm \
  --format='get(networkInterfaces[0].networkIP)')
gcloud compute firewall-rules create enclaiv-vm-to-control-plane \
  --direction=EGRESS --action=ALLOW --rules=tcp:8080 \
  --target-tags=enclaiv-vm \
  --destination-ranges=${CP_IP}/32 --priority=900
```

**Note:** Do NOT apply these rules to the same instance that runs the control plane — the control
plane needs internet access to reach Anthropic/Google APIs.

---

## Phase 2 — Declarative Network Allowlist

Once the MVP is stable, add the network allowlist on top:

```yaml
# enclaiv.yaml
sandbox:
  network:
    allow: [api.anthropic.com, arxiv.org, "*.google.com"]
```

The Go proxy (already built) enforces this. When allowlist is declared:
- VM routes HTTP/HTTPS through proxy (`HTTP_PROXY=http://172.19.0.1:9080`)
- Proxy allows traffic to listed domains, blocks everything else
- Violations are logged via `/violations` API

This is Enclaiv's differentiator — developers declare their agent's network footprint.
Security team audits the YAML. Violations are logged.

---

## Verification Checklist

```bash
# 1. Control plane healthy
curl http://localhost:8080/healthz

# 2. Direct LLM call (no VM)
curl -s -X POST http://localhost:8080/sessions \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "test", "task": "hello", "model": "gemini-2.5-flash"}' | python3 -m json.tool

# 3. Docker local mode
enclaiv run --local --no-proxy "what is 2+2?"

# 4. Unikernel (full isolation)
sudo -E KRAFTKIT_NO_CHECK_UPDATES=true kraft run \
  --arch x86_64 --plat qemu --memory 512Mi --network kraft0 \
  --env "SESSION_TOKEN=<sess>" \
  --env "CONTROL_PLANE_URL=http://172.19.0.1:8080" \
  --env "ENCLAIV_TASK=Say hello from a unikernel!"

# 5. Verify no API key in VM
# Agent output should show "Session token: sess_..." NOT any API key
```

# Enclaiv — Progress Tracker

> Updated 2026-03-21

---

## Status Legend
- ✅ Done
- 🔄 In progress
- ⬜ Not started

---

## Environment Setup

### macOS
| Task | Status | Notes |
|------|--------|-------|
| Install Go | ✅ | |
| Install QEMU | ✅ | |
| Install kraft CLI | ✅ | |

### GCP Linux Box
| Task | Status | Notes |
|------|--------|-------|
| Enable Compute Engine API | ✅ | Project: gen-lang-client-0929887998 |
| Create enclaiv-dev instance | ✅ | n2-standard-2, us-central1-a, nested virt + KVM enabled |
| Create firewall rules | ✅ | SSH (22), console (3001), control plane (8080) |
| SSH into instance | ✅ | Ubuntu 22.04.5 LTS |
| Verify /dev/kvm exists | ✅ | crw-rw---- confirmed — hardware isolation active |
| Install Go 1.22+ on Linux box | ✅ | Upgraded from 1.18 → 1.22.5 |
| Install kraft on Linux box | ✅ | kraft 0.12.6 |
| Install Docker + BuildKit on Linux box | ✅ | docker + docker-buildx-plugin |
| Clone repo on Linux box | ✅ | https://github.com/earl562/enclaiv |
| Grow boot disk to 30 GB | ✅ | growpart + resize2fs online, 22 GB free |
| Configure sudoers for kraft run | ✅ | /etc/sudoers.d/enclaiv-kraft — NOPASSWD for kraft run |
| Provision Google AI API key | ✅ | Created via gcloud, scoped to generativelanguage.googleapis.com |
| Persist API key | ✅ | ~/enclaiv/.env → loaded by docker compose --env-file |

### GitHub
| Task | Status | Notes |
|------|--------|-------|
| Create GitHub repo | ✅ | https://github.com/earl562/enclaiv (public, Apache 2.0) |
| Initial commit pushed | ✅ | CLI, proxy, hardening, infra |

---

## Phase 1 — Unikraft VM

| Task | Status | Notes |
|------|--------|-------|
| Create test-agent with Dockerfile + agent.py + Kraftfile | ✅ | kraft provides Python 3.12 runtime |
| `kraft build` custom unikernel | ✅ | Build: 2.0s, initramfs: 41B |
| `kraft run` — output from inside VM | ✅ | "Hello from inside the unikernel!" on KVM, 2.5s total |
| Write enclaiv.yaml parser | ✅ | cli/enclaiv/config.py |
| Write Kraftfile generator from enclaiv.yaml | ✅ | cli/enclaiv/kraftfile.py |
| `enclaiv run` invokes kraft build + run | ✅ | Wired in cli/enclaiv/commands/run.py |
| `enclaiv run` prepends `sudo -E` on Linux | ✅ | Preserves env vars through sudo for CAP_NET_ADMIN |

---

## Phase 2 — Network Proxy (Go)

| Task | Status | Notes |
|------|--------|-------|
| Initialize Go module (`proxy/`) | ✅ | github.com/enclaiv/enclaiv/proxy |
| HTTP CONNECT handler | ✅ | proxy/pkg/httpproxy/proxy.go |
| Domain allowlist logic | ✅ | proxy/pkg/allowlist/allowlist.go |
| Wildcard matching (`*.google.com`) | ✅ | Tested: scholar.google.com → 302 |
| Violations API (GET /violations) | ✅ | Structured JSON logs per blocked request |
| `enclaiv violations` CLI command | ✅ | Rich table output |
| `enclaiv doctor` CLI command | ✅ | Checks kraft, Docker, Go, QEMU |
| Proxy config via allowlist.json | ✅ | proxy/config/allowlist.json — arxiv.org, api.anthropic.com, Google APIs |
| Proxy built and running in Docker | ✅ | docker compose service on ports 9080/9081 |
| Docker ENTRYPOINT+CMD bug fixed | ✅ | command: must contain only flags, not binary path |
| Allowed domain passes through | ✅ | arxiv.org → 301, scholar.google.com → 302 |
| Blocked domain returns 403 | ✅ | evil.com → 403 Forbidden |

---

## Phase 3 — Control Plane

| Task | Status | Notes |
|------|--------|-------|
| FastAPI project setup | ✅ | control-plane/main.py |
| PostgreSQL schema: sessions table | ✅ | id, agent_name, task, model, session_token, status, created_at, messages (JSONB) |
| Session lifecycle endpoints | ✅ | POST /sessions, GET /sessions, GET /sessions/{id} |
| Append messages endpoint | ✅ | POST /sessions/{id}/messages |
| LLM proxy endpoint | ✅ | POST /llm/complete — injects API key, never exposes it to VM |
| Google Gemini provider | ✅ | gemini-* models → generativelanguage.googleapis.com |
| Anthropic provider | ✅ | all other models → api.anthropic.com |
| Streaming SSE (Google) | ✅ | Normalized to `{"type": "text_delta", "text": "..."}` format |
| Streaming SSE (Anthropic) | ✅ | Raw pass-through of content_block_delta events |
| Session token auth | ✅ | Bearer token validated on all protected endpoints |
| Session wired into `enclaiv run` | ✅ | CLI creates session before kraft run, passes SESSION_TOKEN + CONTROL_PLANE_URL into VM |
| ANTHROPIC_API_KEY never enters VM | ✅ | Only 3 env vars pass into VM: SESSION_TOKEN, CONTROL_PLANE_URL, TASK |
| Healthcheck endpoint | ✅ | GET /healthz |
| Docker container + Dockerfile | ✅ | Python 3.12, asyncpg, FastAPI |
| FastAPI 204 body assertion fixed | ✅ | Append messages route uses 200 + return {} |

---

## Phase 4 — Agent Hardening

| Task | Status | Notes |
|------|--------|-------|
| `enclaiv_runner.py` in VM | ✅ | Strips env vars, configures proxy, runs agent via runpy |
| Privilege drop in entrypoint.sh | ✅ | root → nobody |
| Docker fallback mode | ✅ | `enclaiv run --local` runs agent in Docker container |

---

## Phase 5 — Web Console

| Task | Status | Notes |
|------|--------|-------|
| Next.js web app scaffolded | ✅ | web/ — App Router, TypeScript, Tailwind, Framer Motion |
| Marketing site (landing page) | ✅ | /, hero, product sections, nav, footer |
| Console route /console | ✅ | Full agent chat UI |
| Session sidebar | ✅ | List all sessions, relative timestamps, active indicator |
| New session modal | ✅ | Agent name, task, model selector (gemini-2.5-flash / claude-sonnet) |
| Chat interface | ✅ | User messages (right, dark) + assistant messages (left, white) |
| SSE streaming in browser | ✅ | Typing indicator → streaming text → committed message |
| SSE error surfacing fix | ✅ | Error events now show as readable messages, not silent empty bubbles |
| Empty response fallback | ✅ | Shows "Check API keys" message instead of blank bubble |
| Cmd+Enter to send | ✅ | |
| Auto-resize textarea | ✅ | |
| Auto-scroll to latest message | ✅ | |
| Session token map (client-side) | ✅ | Tokens stored in React state keyed by session ID |
| BFF API routes | ✅ | /api/sessions, /api/sessions/[id], /api/sessions/[id]/chat, /api/sessions/[id]/messages |
| CONTROL_PLANE_URL proxied via BFF | ✅ | Control plane URL never exposed to browser |
| Next.js standalone output | ✅ | output: "standalone" in next.config.ts |
| Web Dockerfile | ✅ | Multi-stage: node:20-alpine builder + production runner |
| Console link in nav | ✅ | Nav bar → Console |
| Web service in docker compose | ✅ | Port 3001, depends on control-plane healthcheck |
| GCP firewall rule for port 3001 | ✅ | enclaiv-web-console |
| Full stack deployed and running | ✅ | http://34.61.100.189:3001/console |
| End-to-end agent response confirmed | ✅ | gemini-2.5-flash streaming through control plane to browser |

---

## Observability

| Task | Status | Notes |
|------|--------|-------|
| Prometheus scraper | ✅ | Port 9090 — scrapes proxy /metrics + control-plane /metrics |
| Grafana dashboards | ✅ | Port 3000 — admin/admin |
| Proxy violations metrics | ✅ | Exposed on port 9081 |
| Alert rules | ✅ | monitoring/alerts.yml |

---

## What's Next

| Task | Priority | Notes |
|------|----------|-------|
| kraft bridge networking on GCP | High | kraft0 bridge needed for VM ↔ proxy routing; fallback to QEMU user-mode (10.0.2.2) works |
| VPC egress firewall rules | High | Block VM egress except → control plane :8080 |
| End-to-end unikernel smoke test | High | `enclaiv run` → VM → control plane → Gemini → browser |
| Bytecode hardening (compileall) | Medium | Delete .py files from VM image, run .pyc only |
| Multi-turn conversation in VM | Medium | Agent SDK calling /llm/complete in a loop |
| Session status updates (active → done) | Medium | Mark session complete when agent exits |
| Anthropic API key | Low | Set ANTHROPIC_API_KEY for Claude model support |

---

## Session Log

| Date | What happened |
|------|--------------|
| 2026-03-18 | GCP instance created, KVM confirmed, Go + kraft installed |
| 2026-03-18 | Full codebase built: CLI (Python), Proxy (Go), hardening, infra |
| 2026-03-18 | Proxy tested locally: allowed/blocked/wildcard domains all work |
| 2026-03-18 | CLI tested: `enclaiv doctor`, `enclaiv init`, `enclaiv violations` all work |
| 2026-03-18 | First unikernel running on KVM — "Hello from inside the unikernel!" |
| 2026-03-18 | Proxy built and tested on Linux box: arxiv.org allowed, evil.com blocked |
| 2026-03-20 | Control plane built: FastAPI + PostgreSQL, session lifecycle, LLM proxy with streaming |
| 2026-03-20 | `enclaiv run` wired to control plane: creates session before kraft run |
| 2026-03-20 | docker-compose updated: Redis removed, web service added, proxy config wired |
| 2026-03-20 | Fixed proxy Docker ENTRYPOINT+CMD bug — allowlist.json now loads correctly |
| 2026-03-20 | GCP boot disk grown 9.6 GB → 30 GB online (growpart + resize2fs) |
| 2026-03-20 | kraft run now uses `sudo -E` on Linux for CAP_NET_ADMIN |
| 2026-03-20 | Web console built: full chat UI at /console with SSE streaming |
| 2026-03-20 | FastAPI 204 body assertion fixed, full stack deployed to GCP |
| 2026-03-21 | Fixed SSE error surfacing — silent empty bubbles replaced with error messages |
| 2026-03-21 | Provisioned Google AI API key via gcloud, persisted to ~/enclaiv/.env |
| 2026-03-21 | End-to-end confirmed: agent responds via gemini-2.5-flash through control plane |

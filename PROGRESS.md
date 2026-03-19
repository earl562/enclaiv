# Enclaiv — Progress Tracker

> Update this as you complete each step. Date each entry.

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
| Create enclaiv-dev instance | ✅ | n2-standard-2, us-central1-a, nested virt enabled |
| Create firewall rule | ✅ | allow-ssh-enclaiv, tcp:22 |
| SSH into instance | ✅ | Ubuntu 22.04.5 LTS |
| Verify /dev/kvm exists | ✅ | crw-rw---- confirmed — hardware isolation active |
| Install Go on Linux box | ✅ | go1.18.1 linux/amd64 |
| Install kraft on Linux box | ✅ | kraft 0.12.6, go1.25.7 (Mar 18) |
| Upgrade Go to 1.22+ on Linux box | 🔄 | Default apt installs 1.18 — needs upgrade |
| Install Docker + BuildKit on Linux box | 🔄 | Required for kraft build from Dockerfile |
| Clone repo on Linux box | 🔄 | https://github.com/earl562/enclaiv |

### GitHub
| Task | Status | Notes |
|------|--------|-------|
| Create GitHub repo | ✅ | https://github.com/earl562/enclaiv (public, Apache 2.0) |
| Initial commit pushed | ✅ | 49 files, 5615 lines — CLI, proxy, hardening, infra |

### Local Testing (macOS)
| Task | Status | Notes |
|------|--------|-------|
| Build Go proxy binary | ✅ | bin/enclaiv-proxy (9.2MB) |
| Proxy: allowed domain passes | ✅ | arxiv.org → 301 |
| Proxy: blocked domain returns 403 | ✅ | evil.com → 403 Forbidden |
| Proxy: wildcard matching works | ✅ | scholar.google.com → 302 (via *.google.com) |
| Violations API returns blocked requests | ✅ | GET /violations → JSON with evil.com violation |
| Install enclaiv CLI | ✅ | pip install -e . → enclaiv 0.1.0 |
| enclaiv doctor | ✅ | kraft, Docker, Go, QEMU all ✓ |
| enclaiv init | ✅ | Scaffolds agent.py, enclaiv.yaml, Dockerfile, requirements.txt |
| enclaiv violations | ✅ | Rich table showing blocked requests from proxy |

---

## Phase 1 — First Unikraft VM

| Task | Status | Notes |
|------|--------|-------|
| Run pre-built Python unikernel (`kraft run unikraft.org/python3.12`) | ⬜ | Skipped — pre-built not available for qemu/x86_64 |
| Create test-agent directory with Dockerfile + agent.py + Kraftfile | ✅ | FROM scratch + agent.py only (kraft provides Python runtime) |
| `kraft build` custom unikernel | ✅ | Build: 2.0s, initramfs: 41B, runtime: python:3.12 |
| `kraft run` — see output from inside VM | ✅ | "Hello from inside the unikernel!" on KVM, 2.5s total |
| Write enclaiv.yaml parser (Python) | ⬜ | |
| Write Kraftfile generator from enclaiv.yaml | ⬜ | |
| `enclaiv run` invokes kraft build + run | ⬜ | |

---

## Phase 2 — Network Proxy (Go)

| Task | Status | Notes |
|------|--------|-------|
| Go Tour completed (basics + goroutines) | ⬜ | |
| Initialize Go module (`proxy/`) | ✅ | github.com/enclaiv/enclaiv/proxy |
| HTTP CONNECT handler | ✅ | proxy/pkg/httpproxy/proxy.go |
| Domain allowlist logic | ✅ | proxy/pkg/allowlist/allowlist.go |
| Wildcard matching (`*.google.com`) | ✅ | Tested: scholar.google.com → 302 |
| Proxy tested on Linux box (GCP) | ✅ | arxiv.org allowed, evil.com blocked with structured JSON logs |
| VM traffic routed through proxy | 🔄 | Proxy works on Linux; VM boots but needs kraft bridge networking (kraft net create needs debugging — bridge driver not found) |
| Allowed domain passes through | ✅ | arxiv.org → 301, scholar.google.com → 302 |
| Blocked domain returns 403 | ✅ | evil.com → 403 Forbidden |

---

## Phase 3 — Credential Proxy + Hardening (MVP)

| Task | Status | Notes |
|------|--------|-------|
| Root CA generation at `enclaiv init` | ⬜ | |
| CA installed in VM trust store during build | ⬜ | |
| Credential proxy TLS termination | ⬜ | |
| API key header injection (x-api-key) | ⬜ | |
| Agent calls Anthropic without seeing key | ⬜ | |
| Bytecode-only execution (.py deleted) | ⬜ | |
| Mandatory deny paths stripped from rootfs | ⬜ | |
| Privilege drop (root → nobody) | ⬜ | |
| Environment stripping (SESSION_TOKEN deleted) | ⬜ | |

**MVP complete when all Phase 3 tasks are ✅**

---

## Phase 4 — Violation Tracking

| Task | Status | Notes |
|------|--------|-------|
| Violation store (in-memory) | ⬜ | |
| Structured JSON logging per blocked request | ⬜ | |
| REST endpoint on proxy: GET /violations | ⬜ | |
| `enclaiv violations` CLI command | ⬜ | |
| `enclaiv doctor` CLI command | ⬜ | |

---

## Phase 5 — Control Plane (skip for MVP)

| Task | Status | Notes |
|------|--------|-------|
| FastAPI project setup | ⬜ | |
| PostgreSQL: conversation history | ⬜ | |
| Redis: rate limiting + session cache | ⬜ | |
| API key auth | ⬜ | |
| Gateway Protocol implementation | ⬜ | |
| File sync via presigned GCS URLs | ⬜ | |

---

## Phase 6 — Docker Fallback + CI/CD + OTel (skip for MVP)

| Task | Status | Notes |
|------|--------|-------|
| `enclaiv run --local` (Docker mode) | ⬜ | |
| GitHub Actions: Go tests | ⬜ | |
| GitHub Actions: Python tests | ⬜ | |
| GitHub Actions: integration test | ⬜ | |
| OpenTelemetry distributed tracing | ⬜ | |

---

## Phase 7 — Launch (skip for MVP)

| Task | Status | Notes |
|------|--------|-------|
| README with architecture diagram | ⬜ | |
| Getting started guide | ⬜ | |
| Demo video | ⬜ | |
| Hacker News Show HN | ⬜ | |

---

## Blockers / Open Questions

| Issue | Status |
|-------|--------|
| Go version on Linux is 1.18 — may need 1.22+ for some features | ⬜ investigate |
| kraft bridge networking: `kraft net create` fails with "no such network: bridge" even with sudo | 🔄 | May need `bridge-utils` or different kraft network driver |

---

## Session Log

| Date | What happened |
|------|--------------|
| 2026-03-18 | GCP instance created, KVM confirmed, Go + kraft installed |
| 2026-03-18 | Full codebase built: CLI (Python), Proxy (Go), hardening, infra |
| 2026-03-18 | Proxy tested locally: allowed/blocked/wildcard domains all work |
| 2026-03-18 | CLI tested: `enclaiv doctor`, `enclaiv init`, `enclaiv violations` all work |
| 2026-03-18 | First unikernel running on KVM! "Hello from inside the unikernel!" — Unikraft Kiviuq 0.20.0 |
| 2026-03-18 | Proxy built and tested on Linux box: arxiv.org allowed, evil.com blocked with structured violation logs |

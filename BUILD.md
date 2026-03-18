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
4. Credential Proxy (Go) — injects API keys into requests *after* they leave the VM; agent never sees the key
5. Control Plane (FastAPI) — auth, history, file sync, fleet management (Phase 5, not MVP)

**MVP = pieces 1–4.** A working agent that runs in a hardware-isolated VM with network filtering and credential injection. 6 weeks in the spec, you're targeting 1 week rough.

---

## Environment Setup (Do This First)

### macOS (your machine — daily development)

```bash
# Go (you'll write the proxy in this)
brew install go

# QEMU (kraft uses this on macOS instead of KVM)
brew install qemu

# kraft CLI (builds and runs unikernel VMs)
curl --proto '=https' --tlsv1.2 -sSf https://get.kraftkit.sh | sh
```

Verify everything installed:
```bash
go version              # want 1.22+
qemu-system-x86_64 --version
kraft version
```

### Linux box (for KVM validation — needed around Day 4)

This is the only place you get real hardware isolation. Costs ~$0.08/hr — stop it when you're not using it.

**Step 1 — Install gcloud if you don't have it:**
```bash
brew install --cask google-cloud-sdk
gcloud init   # walks you through login + project selection
```

If already installed but not logged in:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

**Step 2 — Create the instance:**
```bash
gcloud compute instances create enclaiv-dev \
  --machine-type=n2-standard-2 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --min-cpu-platform="Intel Cascade Lake" \
  --enable-nested-virtualization \
  --zone=us-central1-a \
  --tags=enclaiv-dev
```

The `--enable-nested-virtualization` flag is what gives you `/dev/kvm` inside the VM. Without it, no hardware isolation.

**Step 3 — Open SSH access and connect:**
```bash
MY_IP=$(curl -s -4 icanhazip.com)
gcloud compute firewall-rules create allow-ssh-enclaiv --allow=tcp:22 --target-tags=enclaiv-dev --source-ranges=$MY_IP/32

# SSH in
gcloud compute ssh enclaiv-dev --zone=us-central1-a

# If your home IP changes and you get locked out, update the rule:
MY_IP=$(curl -s -4 icanhazip.com)
gcloud compute firewall-rules update allow-ssh-enclaiv --source-ranges=$MY_IP/32
```

**Step 4 — Inside the Linux box, install the toolchain:**
```bash
# Verify KVM is available (this is the critical check)
ls -la /dev/kvm
# Should show something like: crw-rw---- 1 root kvm ...
# If "No such file or directory" → nested virtualization didn't work, check Step 2

# Install Go
sudo apt update && sudo apt install -y golang-go

# Install kraft
curl --proto '=https' --tlsv1.2 -sSf https://get.kraftkit.sh | sh

# Verify
go version
kraft version
```

**Step 5 — Stop the instance when not in use:**
```bash
gcloud compute instances stop enclaiv-dev --zone=us-central1-a

# Start again later:
gcloud compute instances start enclaiv-dev --zone=us-central1-a
```

---

### Alternative: Create the instance via GCP Console (no CLI needed)

1. Go to **console.cloud.google.com** → select your project
2. Navigate: **Compute Engine → VM instances → Create Instance**
3. Fill in:
   - **Name:** `enclaiv-dev`
   - **Region/Zone:** `us-central1 / us-central1-a`
   - **Machine configuration:** General purpose → **N2** → `n2-standard-2`
   - **CPU platform:** click "CPU platform and GPU" → set minimum CPU platform to **Intel Cascade Lake**
4. Under **Boot disk** → Change:
   - Operating system: **Ubuntu**
   - Version: **Ubuntu 22.04 LTS**
   - Boot disk size: 50 GB is fine
5. Scroll to **Advanced options → VM hardware → Security**:
   - Check **"Enable nested virtualization"** ← this is the critical one
6. Click **Create**
7. Once running, click **SSH** button in the console — opens a browser terminal, no local setup needed

To stop it: VM instances list → three-dot menu next to `enclaiv-dev` → **Stop**.
To start it again: same menu → **Start/Resume**.

SSH in and run the same three installs (Go, QEMU, kraft).
Confirm KVM is available: `ls -la /dev/kvm` — if the file exists, you have hardware isolation.

> **Note on macOS vs Linux:** On macOS, kraft uses QEMU emulation (no hardware isolation, but same unikernel image). On Linux with KVM, it uses hardware isolation. You develop on Mac, validate isolation on Linux. The agent code and `enclaiv.yaml` are identical in both cases.

---

## Repo Structure

Create this now. Empty directories are fine — you'll fill them in as you go.

```
enclaiv/
  cli/                  # Python: enclaiv CLI (Typer)
  proxy/                # Go: Network Proxy + Credential Proxy
  control-plane/        # Python: FastAPI (Phase 5, skip for now)
  templates/            # Starter agent templates
  hardening/            # entrypoint.sh, strip_rootfs.py, mandatory_denies.yaml
  monitoring/           # Prometheus, Grafana, alerts (Phase 6, skip for now)
  terraform/            # GCP infra (Phase 6, skip for now)
  docs/
  docker-compose.yml
  Makefile
  README.md
  BUILD.md              # this file
```

```bash
mkdir -p enclaiv/{cli,proxy,control-plane,templates,hardening,monitoring,terraform,docs}
cd enclaiv
git init
```

---

## Phase 1 — First Unikraft VM (Days 1–2)

**Goal:** Get a Python agent running inside a Unikraft unikernel. When you see output from inside the VM, Phase 1 is done.

**Why this first:** Everything else depends on agents actually running in VMs. If this doesn't work, nothing works.

### Step 1.1 — Install Docker + BuildKit on the Linux box

kraft uses Docker's BuildKit to process Dockerfiles into unikernel root filesystems. Install it first:

```bash
sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
```

Then start BuildKit (runs as a Docker container):

```bash
docker run -d --name buildkitd --privileged moby/buildkit:latest
```

Tell kraft where to find BuildKit:

```bash
export KRAFTKIT_BUILDKIT_HOST=docker-container://buildkitd
echo 'export KRAFTKIT_BUILDKIT_HOST=docker-container://buildkitd' >> ~/.bashrc
```

Verify:

```bash
docker ps | grep buildkit
```

You should see the buildkitd container running.

### Step 1.2 — Build your own unikernel from a Dockerfile

Create a test agent directory:

```bash
mkdir ~/test-agent && cd ~/test-agent
```

Create three files:

**agent.py:**
```python
print("Hello from inside the unikernel!")
import os
print(f"Environment vars: {list(os.environ.keys())}")
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim
COPY agent.py /app/agent.py
WORKDIR /app
CMD ["python3", "/app/agent.py"]
```

**Kraftfile** (kraft's config — you'll generate this automatically later):
```yaml
spec: v0.6
runtime: python:3.11
rootfs: ./Dockerfile
cmd: ["/usr/bin/python3", "/app/agent.py"]
```

Build and run:
```bash
kraft build --arch x86_64 --plat qemu
kraft run --arch x86_64 --plat qemu --memory 512Mi
```

### Step 1.3 — Deploy code to the Linux box and test

**On your Mac** — create the tarball and upload:
```bash
cd /Users/earlperry/Desktop/Projects/enclaiv
tar czf /tmp/enclaiv.tar.gz --exclude='.git' --exclude='bin' --exclude='.ruff_cache' --exclude='.claude' --exclude='__pycache__' .
gcloud compute scp /tmp/enclaiv.tar.gz enclaiv-dev:~/enclaiv.tar.gz --zone=us-central1-a
```

**On the Linux box** — extract, install Docker + BuildKit, build everything:
```bash
# Extract the code
mkdir -p ~/enclaiv && cd ~/enclaiv && tar xzf ~/enclaiv.tar.gz

# Install Docker
sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker

# Start BuildKit (kraft needs this to process Dockerfiles)
docker run -d --name buildkitd --privileged moby/buildkit:latest
export KRAFTKIT_BUILDKIT_HOST=docker-container://buildkitd
echo 'export KRAFTKIT_BUILDKIT_HOST=docker-container://buildkitd' >> ~/.bashrc

# Build the Go proxy
cd ~/enclaiv/proxy && go build -o ~/enclaiv/bin/enclaiv-proxy cmd/proxy/main.go

# Start the proxy in background
cd ~/enclaiv
mkdir -p bin
cp bin/allowlist.json bin/credentials.json . 2>/dev/null || true
./bin/enclaiv-proxy --config allowlist.json --cred-config credentials.json &

# Build and run the unikernel
mkdir -p ~/test-agent && cd ~/test-agent
cat > agent.py << 'EOF'
print("Hello from inside the unikernel!")
import os
print(f"Environment vars: {list(os.environ.keys())}")
EOF
cat > Dockerfile << 'EOF'
FROM python:3.11-slim
COPY agent.py /app/agent.py
WORKDIR /app
CMD ["python3", "/app/agent.py"]
EOF
cat > Kraftfile << 'EOF'
spec: v0.6
runtime: python:3.11
rootfs: ./Dockerfile
cmd: ["/usr/bin/python3", "/app/agent.py"]
EOF

kraft build --arch x86_64 --plat qemu
kraft run --arch x86_64 --plat qemu --memory 512Mi
```

**Success:** You see `Hello from inside the unikernel!` — a Python agent ran inside a hardware-isolated VM on KVM.

**Success:** You see `Hello from inside the unikernel!` printed to your terminal.

### Step 1.3 — Understand what just happened

When `kraft build` ran:
1. It processed your Dockerfile using BuildKit
2. Packaged the result (Python runtime + your script) as a CPIO archive (a filesystem image)
3. Linked it against the Unikraft kernel (lwIP network stack, musl libc, Python interpreter)
4. Produced a single binary: the unikernel image

When `kraft run` ran:
1. QEMU (or KVM on Linux) booted the unikernel image as a VM
2. The VM has its own kernel, its own network stack, its own filesystem
3. Your `agent.py` ran inside that isolated environment

The VM has no shell. No SSH. No package manager. Only what you put in the Dockerfile.

### Step 1.4 — enclaiv.yaml parser (Python CLI starts here)

Now write the code that reads `enclaiv.yaml` and generates a Kraftfile.

```bash
cd ../cli
pip install typer pyyaml
```

**cli/enclaiv/config.py** — reads and validates enclaiv.yaml
**cli/enclaiv/kraftfile.py** — generates a Kraftfile from the parsed config
**cli/enclaiv/commands/run.py** — `enclaiv run` command that calls kraft

The enclaiv.yaml format (from the spec):
```yaml
name: my-research-agent
runtime: python:3.11
sandbox:
  network:
    allow: [api.anthropic.com, arxiv.org, "*.google.com"]
    deny: []
  filesystem:
    writable: [./output, /tmp]
    deny_read: [~/.ssh, ~/.aws, .env]
  resources:
    memory: 512mb
    cpu: 1
    timeout: 300s
credentials:
  - name: ANTHROPIC_API_KEY
    source: env
```

Your CLI reads this, generates the Kraftfile, calls `kraft build`, calls `kraft run`.

**Phase 1 is complete when:** `enclaiv run "do something"` reads your enclaiv.yaml, builds a unikernel, and boots it.

---

## Phase 2 — Network Proxy in Go (Days 3–4)

**Goal:** Every byte the VM sends to the network goes through your Go proxy. Allowed domains pass through. Everything else gets blocked and logged.

**Why Go:** Performance matters for a proxy — it's in the critical path of every network request. Go's goroutines make it trivial to handle concurrent connections. The `net` and `net/http` packages have exactly what you need.

### Step 2.1 — Learn just enough Go

Do the Go Tour (**go.dev/tour**) sections in this order:
1. Basics (A Tour of Go → Basics) — 45 min
2. Methods and Interfaces — 30 min
3. Concurrency (goroutines + channels) — 45 min

Then stop the tutorial and start building. You learn Go by writing Go.

Key concepts you need for the proxy:
- `net.Listen` / `net.Dial` — open TCP connections
- `http.ListenAndServe` / `http.HandleFunc` — HTTP server
- `http.Hijacker` — take over a raw TCP connection from an HTTP handler (critical for CONNECT tunnels)
- `io.Copy` — copy bytes between two connections (this is how you pipe traffic)
- goroutines — `go func()` for concurrent connection handling

### Step 2.2 — Initialize the Go module

```bash
cd proxy
go mod init github.com/enclaiv/enclaiv/proxy
```

Structure:
```
proxy/
  cmd/proxy/main.go          # entry point
  pkg/allowlist/allowlist.go # domain matching logic
  pkg/http/proxy.go          # HTTP CONNECT handler
  pkg/violations/store.go    # violation logging
  go.mod
```

### Step 2.3 — How HTTP CONNECT works (read this carefully)

When an HTTPS request goes through a proxy, the client sends:

```
CONNECT api.anthropic.com:443 HTTP/1.1
Host: api.anthropic.com:443
```

The proxy responds:
```
HTTP/1.1 200 Connection Established
```

Then the proxy becomes a dumb pipe — it copies bytes from the client to the server and back. The proxy never sees the HTTPS content. TLS is end-to-end between the client and the destination.

This is what `http.Hijacker` does: it lets you "hijack" the underlying TCP connection from Go's HTTP server, so you can pipe raw bytes.

Your proxy flow:
1. Receive `CONNECT host:port` request
2. Extract the hostname
3. Check against allowlist
4. If blocked: return `403 Forbidden`, log the violation
5. If allowed: dial the destination, hijack the client connection, copy bytes bidirectionally

### Step 2.4 — The allowlist logic

Domain matching rules (from the spec):
- Exact match: `api.anthropic.com` matches only `api.anthropic.com`
- Wildcard: `*.google.com` matches `scholar.google.com` and `www.google.com` but NOT `google.com`
- Default: if nothing matches → **deny**

Your `pkg/allowlist/allowlist.go` needs:
```go
type Allowlist struct {
    allowed []string
    denied  []string
}

func (a *Allowlist) IsAllowed(host string) bool {
    // Check denied patterns first
    // Then check allowed patterns
    // Default: deny
}

func matchDomain(pattern, host string) bool {
    // Handle "*.example.com" wildcards
}
```

### Step 2.5 — Violation store

Every blocked request gets recorded. Developers query these with `enclaiv violations`.

```go
type Violation struct {
    Timestamp   time.Time
    AgentID     string
    SessionID   string
    Destination string
    Reason      string
}

type ViolationStore struct {
    mu         sync.RWMutex
    violations []Violation
}
```

Use `slog` (Go's standard structured logger) to also write violations to stdout as JSON.

### Step 2.6 — Connect the VM to the proxy

Set environment variables in the VM's entrypoint before starting the agent:

```bash
export HTTP_PROXY=http://HOST_IP:9080
export HTTPS_PROXY=http://HOST_IP:9080
```

`HOST_IP` is the host machine's IP as seen from inside the VM. On macOS with QEMU, this is typically `10.0.2.2`. On Linux with KVM it's the host's bridge IP.

**Phase 2 is complete when:**
- `kraft run` with HTTP_PROXY set, agent tries `curl arxiv.org` → succeeds
- Agent tries `curl evil.com` → proxy returns 403, violation is logged

---

## Phase 3 — Credential Proxy + Hardening (Days 5–6)

**Goal:** The agent calls the Anthropic API without knowing the API key. The key is injected by the proxy after the traffic leaves the VM. Plus: bytecode-only execution, privilege drop, mandatory deny paths.

### Step 3.1 — How credential injection works

This is the hardest architectural piece. Here's what actually happens:

```
VM: anthropic.Anthropic()     ← no API key set
VM: sends request to api.anthropic.com:443
VM → Network Proxy: CONNECT api.anthropic.com:443
Network Proxy: sees api.anthropic.com is allowed AND needs credential injection
Network Proxy: routes to Credential Proxy instead of connecting directly
Credential Proxy: terminates TLS connection from VM
Credential Proxy: adds "x-api-key: sk-ant-xxxx" header
Credential Proxy: opens new TLS connection to api.anthropic.com
Credential Proxy: forwards request + gets response
Response flows back: Anthropic → Credential Proxy → Network Proxy → VM
```

The credential proxy is doing **TLS termination** — it's a man-in-the-middle between the VM and Anthropic. For this to work without TLS errors inside the VM:

1. At `enclaiv init`, generate a root CA certificate (self-signed)
2. During `kraft build`, install that root CA into the VM's trust store (`/etc/ssl/certs/`)
3. The credential proxy uses that CA to sign a certificate for `api.anthropic.com`
4. The VM trusts the proxy's cert because it was signed by the CA it trusts
5. The proxy has a valid cert from Anthropic because it opens a fresh TLS connection outbound

**Week-1 shortcut:** If TLS MITM is slowing you down, start with an HTTP-only test. Have your agent call `http://api.anthropic.com` (not HTTPS) — no TLS, so no cert needed, just header injection. Get the flow working, then add TLS on top.

### Step 3.2 — Credential proxy structure

```
proxy/
  pkg/credentials/injector.go   # reads credentials, injects headers per domain
  pkg/credentials/ca.go         # root CA generation and cert signing
```

The injector needs to know which header to add per provider:
- Anthropic: `x-api-key: <value>`
- OpenAI: `Authorization: Bearer <value>`
- Others: configurable

### Step 3.3 — Hardening: bytecode-only execution

Add to your Dockerfile **before** `kraft build`:

```dockerfile
# Compile Python source to bytecode
RUN python3 -m compileall -b /app

# Delete source files — only .pyc remains
RUN find /app -name '*.py' -not -name '__pycache__' -delete
```

Why: an attacker who compromises the agent can't read or modify the source code. They can only run the compiled bytecode.

### Step 3.4 — Hardening: mandatory deny paths

These paths are stripped from the VM's filesystem during `kraft build`. The agent cannot read them even if it tries.

Create `hardening/mandatory_denies.yaml`:
```yaml
deny_paths:
  - ~/.ssh/
  - ~/.aws/
  - ~/.config/gcloud/
  - .env
  - .bashrc
  - .bash_profile
  - .zshrc
  - .profile
  - .gitconfig
  - .git/config
  - .git/hooks/
  - .vscode/
  - .idea/
  - enclaiv.yaml
  - .enclaiv/
```

Create `hardening/strip_rootfs.py` — a script that walks the VM rootfs (CPIO archive) and removes any of these paths before the image is booted.

### Step 3.5 — Hardening: privilege drop + environment stripping

Create `hardening/entrypoint.sh` — this runs inside the VM before the agent:

```bash
#!/bin/sh
# 1. Read the tokens we need
SESSION_TOKEN="$SESSION_TOKEN"
CONTROL_PLANE_URL="$CONTROL_PLANE_URL"
SESSION_ID="$SESSION_ID"

# 2. Strip ALL environment variables
# (the agent should inherit nothing from boot)
# This is done in the Python entrypoint wrapper, not shell

# 3. Drop privileges from root to unprivileged user
exec su -s /bin/sh nobody -c "python3 /app/enclaiv_runner.pyc"
```

Create `hardening/enclaiv_runner.py` — the actual Python wrapper:

```python
import os

# Read tokens before stripping env
_SESSION_TOKEN = os.environ.pop('SESSION_TOKEN', None)
_CONTROL_PLANE_URL = os.environ.pop('CONTROL_PLANE_URL', None)
_SESSION_ID = os.environ.pop('SESSION_ID', None)

# Set proxy (already set by entrypoint.sh, but belt-and-suspenders)
os.environ['HTTP_PROXY'] = 'http://10.0.2.2:9080'
os.environ['HTTPS_PROXY'] = 'http://10.0.2.2:9080'

# Now run the actual agent
import runpy
runpy.run_path('/app/agent.pyc', run_name='__main__')
```

**Phase 3 (MVP) is complete when:**
- Agent runs in a Unikraft VM (QEMU on Mac, KVM on Linux)
- Agent's network traffic goes through your Go proxy
- Unlisted domains are blocked and logged
- API key is injected by the proxy — the agent never sees it
- VM filesystem has no `~/.ssh`, `~/.aws`, `.env`
- VM process runs as unprivileged user
- Source code is bytecode-only

---

## Phase 4 — Violation Tracking + CLI Commands (Day 7)

**Goal:** Developers can see exactly what the agent tried to do.

### `enclaiv violations <agent-name>`

Queries the violation store and prints a human-readable summary:

```
3 network violations in last session:
  BLOCKED  openai.com:443       (not in allowlist)  14:30:01
  BLOCKED  stackoverflow.com:443 (not in allowlist)  14:30:03
  BLOCKED  evil.com:443         (not in allowlist)   14:30:05
```

The violation store (built in Phase 2) exposes an HTTP endpoint on the proxy that the CLI queries. Simple REST: `GET /violations?agent=my-research-agent&session=sess_abc123`.

### `enclaiv doctor`

Checks all dependencies are installed and working:

```
[✓] kraft CLI: v0.9.1
[✓] KVM: available (/dev/kvm)      ← shows QEMU fallback on macOS
[✓] Docker: v24.0.5 (for --local fallback)
[✓] Go: 1.22.0
[✗] ANTHROPIC_API_KEY: not set
```

---

## Phase 5 — Control Plane (Weeks 9–10, after MVP)

Skip this for the one-week sprint. Come back to it.

**What it adds:**
- Auth (API keys for accessing your deployed agents)
- Rate limiting (sliding window, stored in Redis)
- LLM conversation history (PostgreSQL — enables resuming if VM crashes)
- File sync (presigned GCS URLs so agents can persist output)

**Stack:** FastAPI + PostgreSQL + Redis + Cloud Run

The control plane is why the Gateway Protocol abstraction matters. Your agent code calls `gateway.invoke_llm(messages)` — in production this goes to the control plane, which owns the full conversation history and proxies to the LLM. In local dev, it calls the LLM directly. Same agent code, different backend.

---

## Phase 6 — Docker Fallback + CI/CD + Observability (Weeks 11–12)

**Docker fallback (`--local` flag):**
The spec says: macOS devs use Docker for local iteration. Production runs Unikraft on Linux.
The `--local` flag runs the agent in Docker with the same proxy and credential injection, but without the unikernel VM. Faster iteration, less isolation.

**GitHub Actions CI:**
- Unit tests for Go proxy (`go test -race ./...`)
- Unit tests for Python CLI (`pytest`)
- Integration test: boot a test agent, verify proxy blocks unauthorized domain

**OpenTelemetry:**
Distributed tracing across CLI → VM boot → proxy → LLM call → result. A single trace ID follows the entire request. You can correlate "this blocked network request" with "this specific tool call from the LLM."

---

## Phase 7 — Launch (Weeks 13–14)

**The GitHub README needs to show:**
1. Installation (`pip install enclaiv`)
2. One `enclaiv.yaml` example
3. One `enclaiv run` output with the security summary
4. The architecture diagram (already in the spec as a Mermaid diagram)
5. Comparison table vs Docker/OpenShell/E2B

**Demo video:** Screen recording of `enclaiv run`, showing:
- VM booting (42ms)
- Agent running
- Violations summary ("0 blocked" when clean, "3 blocked" with evil.com in there)

**Launch targets:** Hacker News "Show HN", r/selfhosted, r/MachineLearning, Anthropic Discord

---

## Key Concepts Reference

### HTTP CONNECT method
Used by all HTTPS traffic going through a proxy. Client sends `CONNECT host:port`, proxy opens TCP connection to destination, responds `200`, then becomes a dumb byte pipe. Proxy never sees the encrypted content. See RFC 7230.

### SOCKS5 protocol
Alternative to HTTP CONNECT. Used by non-HTTP traffic (databases, custom protocols). RFC 1928 is only 10 pages — read it directly. Needed for Phase 2 but can be deferred after HTTP CONNECT works.

### KVM hardware isolation
Kernel-based Virtual Machine. Uses CPU hardware (Intel VT-x / AMD-V) to run a guest VM with a completely separate kernel. The host kernel and guest kernel are in separate address spaces enforced by the CPU. An exploit in the guest kernel cannot affect the host. This is what makes Enclaiv's isolation "hardware-level" vs Docker's "process-level."

### Unikraft unikernels
A unikernel is a single-purpose OS image: it contains only the OS components the app needs (Python interpreter, network stack, TLS). No shell, no SSH, no package manager, no init system. This minimizes attack surface. Unikraft builds these from Dockerfiles. Boot time: 10-50ms (vs 30-60s for a full Linux VM).

### The Gateway Protocol
The abstraction that makes the same agent code work in local dev (macOS, Docker) and production (Linux, Unikraft VM):

```
Production: Agent → ControlPlaneGateway → Control Plane → LLM Provider
Local dev:  Agent → DirectGateway → LLM Provider directly
```

Agent code calls `gateway.invoke_llm(messages)` and never knows which backend it's talking to.

### TLS termination (credential proxy)
The credential proxy sits between the VM and the LLM provider. It terminates the VM's TLS connection (acting as the "server"), inspects/modifies the HTTP request (adds API key header), then opens a new TLS connection to the real LLM provider (acting as the "client"). For the VM to trust the proxy's TLS cert, a root CA is generated at `enclaiv init` and installed in the VM's trust store during `kraft build`.

### Stateless LLM proxying
The VM only sends *new* messages. The control plane owns the full conversation history in PostgreSQL. This means: (1) if the VM crashes, you can spin up a fresh VM and resume — the history is in the database; (2) the VM never accumulates state; (3) the control plane can enforce token budgets and rate limits.

---

## Resources

| Topic | Resource |
|-------|----------|
| Go language | [go.dev/tour](https://go.dev/tour) — 2–3 hours |
| Go standard library | [pkg.go.dev/std](https://pkg.go.dev/std) — reference |
| Unikraft docs | [unikraft.org/docs](https://unikraft.org/docs) |
| Kraftfile spec v0.6 | [unikraft.org/docs/cli/reference/kraftfile/v0.6](https://unikraft.org/docs/cli/reference/kraftfile/v0.6) |
| HTTP CONNECT | RFC 7230 Section 4.3.6 |
| SOCKS5 | RFC 1928 (~10 pages, read it directly) |
| KVM overview | [Red Hat: What is KVM](https://www.redhat.com/en/topics/virtualization/what-is-KVM) |
| Anthropic srt (study this) | [github.com/anthropics/anthropic-quickstarts](https://github.com/anthropics/anthropic-quickstarts) — look at the sandbox runtime source |
| Firecracker design | [github.com/firecracker-microvm/firecracker/blob/main/docs/design.md](https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md) — good background on micro-VMs |

---

## Spec Gaps (Things the Spec Doesn't Tell You)

These are design decisions the spec left open. Here's how to fill them in:

**1. TLS in the credential proxy**
The spec shows header injection but doesn't explain the TLS mechanics. Answer: you need a root CA generated at `enclaiv init`, installed in the VM trust store during `kraft build`, used by the credential proxy to sign certs for domains it intercepts. Week-1 shortcut: test with HTTP first, add TLS after.

**2. HOST_IP inside the VM**
The proxy runs on the host. What IP does the VM use to reach it? On QEMU/macOS: `10.0.2.2` (QEMU's default gateway IP). On KVM/Linux: the host's KVM bridge IP, usually `192.168.122.1`. Your CLI needs to detect which mode it's in and set `HTTP_PROXY` accordingly.

**3. entrypoint.sh full implementation**
The spec mentions it but doesn't show the full file. It needs to: (1) read SESSION_TOKEN/CONTROL_PLANE_URL/SESSION_ID into variables, (2) strip them from the environment, (3) set HTTP_PROXY/HTTPS_PROXY to point to the host proxy, (4) drop from root to `nobody` user via `su` or `setuid`, (5) exec the agent.

**4. Warm pool lifecycle**
The spec shows the Go code for the warm pool but doesn't explain the VM lifecycle. Answer: each VM is ephemeral. You pre-boot VMs with a generic base image (no agent code yet). When a request comes in, you assign a warm VM to it, send the agent code + task in, run it, then *destroy* the VM. The next warm VM is for a completely different session. No VM is ever reused.

**5. Which Python packages work on Unikraft**
The Unikraft Python runtime supports the standard library and pure-Python packages. C-extension packages (numpy, pandas) require cross-compilation for the Unikraft target — `pip install` in the Dockerfile handles this if Unikraft's Python runtime supports that extension. Not everything works yet. Test your dependencies early.

---

*Questions? Stuck? Ping Claude. That's what it's here for.*

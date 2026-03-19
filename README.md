# Enclaiv

Hardware-isolated sandboxing for AI agents.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Built with Unikraft](https://img.shields.io/badge/built%20with-Unikraft-orange.svg)](https://unikraft.org)

---

## The problem

AI agents are given API keys, cloud credentials, and network access so they can do useful work. When an agent is compromised — or simply misconfigured — it can exfiltrate secrets, make unauthorized API calls, or reach infrastructure it was never meant to touch. The blast radius is whatever the agent had access to.

Docker containers are the default answer. They are not sufficient. Containers share the host kernel. A kernel exploit inside a container can affect the host. An agent running in a container is one CVE away from breaking out.

Full virtual machines provide real hardware isolation, but they are slow to boot, heavy to run, and operationally complex. The gap between "too permeable" and "too slow" is where most teams give up and accept the risk.

Enclaiv closes that gap. Each agent runs in its own Unikraft unikernel VM — hardware-isolated, boots in under 50ms, with a ~5MB footprint. The agent's network access is declared upfront in a config file. Credentials are never passed into the VM. Every blocked request is logged.

---

## What Enclaiv does

### Network proxy

A Go-based proxy sits between every agent VM and the network. Before the agent boots, you declare which domains it is allowed to reach in `enclaiv.yaml`. Every outbound request is checked against that list. Allowed domains pass through. Everything else receives a `403` and is written to the violation log. The agent cannot reach a domain that is not on the list, regardless of what the agent code does.

### Credential injection

API keys are injected outside the VM boundary. The agent calls the Anthropic API (or any other provider) without an API key set in its environment. The request leaves the VM, hits the credential proxy, and the key is added to the request headers there — after the traffic has already left the sandbox. The agent never holds the credential. A compromised agent cannot exfiltrate a key it was never given.

The credential proxy performs TLS termination using a root CA generated at `enclaiv init` and installed in the VM's trust store during build. From the agent's perspective, the TLS handshake succeeds normally.

### Unikernel isolation

Each agent runs in its own Unikraft unikernel VM. A unikernel is a single-purpose OS image: it contains only the components the application needs — Python interpreter, network stack, TLS — and nothing else. No shell. No SSH daemon. No package manager. No init system.

On Linux with KVM, this is hardware isolation: the host kernel and guest kernel run in separate address spaces enforced by the CPU. An exploit inside the VM cannot reach the host. On macOS, Enclaiv uses QEMU emulation — same unikernel image, suitable for development.

Boot time is under 50ms. The image footprint is approximately 5MB, compared to hundreds of megabytes for a minimal Linux VM.

### Violation tracking

Every blocked network request is recorded as structured JSON: timestamp, agent ID, session ID, destination, protocol, and reason. The `enclaiv violations` command queries the proxy's REST endpoint and prints a summary. You can filter by agent or session. The full audit trail persists for the lifetime of the proxy process.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                 Host System                  │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Agent VM │  │ Agent VM │  │ Agent VM │  │
│  │ (Unikr.) │  │ (Unikr.) │  │ (Unikr.) │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │        │
│  ┌────▼──────────────▼──────────────▼────┐  │
│  │         Network Proxy (Go)            │  │
│  │    Allowlist ─ Credential Inject      │  │
│  │    Violation Log ─ Audit Trail        │  │
│  └────────────────┬──────────────────────┘  │
└───────────────────┼─────────────────────────┘
                    │
               ┌────▼────┐
               │ Internet│
               └─────────┘
```

The agent VM has no route to the network except through the proxy. The proxy is the only process that holds credentials. The VM is destroyed after the session ends.

---

## Quick start

### Prerequisites

```bash
# macOS
brew install go qemu
curl --proto '=https' --tlsv1.2 -sSf https://get.kraftkit.sh | sh

# Verify
go version        # want 1.22+
kraft version
qemu-system-x86_64 --version
```

For hardware isolation (KVM), you need a Linux host with `/dev/kvm` available. See [BUILD.md](BUILD.md) for GCP setup instructions.

### Install the CLI

```bash
git clone https://github.com/earl562/enclaiv.git
cd enclaiv
pip install -e cli/
```

### Initialize an agent

```bash
mkdir my-agent && cd my-agent
enclaiv init
```

This scaffolds `agent.py`, `enclaiv.yaml`, `Dockerfile`, and `requirements.txt`.

### Configure the sandbox

Edit `enclaiv.yaml`:

```yaml
name: my-research-agent
runtime: python:3.11
sandbox:
  network:
    allow: [api.anthropic.com, arxiv.org, "*.google.com"]
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

### Build and run

```bash
# Start the network proxy
cd proxy
go build -o bin/enclaiv-proxy ./cmd/proxy
./bin/enclaiv-proxy --config ../my-agent/enclaiv.yaml &

# Run the agent
cd ../my-agent
enclaiv run
```

### Inspect violations

```bash
enclaiv violations my-research-agent
```

```
3 network violations in last session:
  BLOCKED  openai.com:443         not in allowlist   14:30:01
  BLOCKED  stackoverflow.com:443  not in allowlist   14:30:03
  BLOCKED  evil.com:443           not in allowlist   14:30:05
```

### Check your environment

```bash
enclaiv doctor
```

```
[✓] kraft CLI: v0.12.6
[✓] KVM: available (/dev/kvm)
[✓] Docker: v24.0.5
[✓] Go: 1.22.0
[✓] ANTHROPIC_API_KEY: set
```

---

## What we hope to accomplish

Every AI agent should run in its own hardware-isolated sandbox by default — not as a premium feature, not as a security afterthought, but as the baseline.

Today, the standard practice is to give agents credentials and trust that the code behaves. That works until it doesn't. A single misconfiguration, a compromised dependency, or an unexpected model behavior can turn a helpful agent into a liability.

We want sandboxing to be as easy as containerization. One config file to declare what the agent can reach. One command to boot a secure environment. No credentials inside the VM. No kernel shared with the host.

The longer-term goal is zero-trust agent infrastructure: agents get compute and declared capabilities, not credentials. The credentials live in the proxy. The isolation is enforced by hardware. The audit trail is automatic.

Enclaiv is open-source because this infrastructure should be available to everyone building with AI agents, not just teams with dedicated security engineers.

---

## Tech stack

| Component | Technology |
|-----------|------------|
| Agent runtime | [Unikraft](https://unikraft.org) unikernel VMs |
| Network proxy | Go (`net/http`, `net.Hijacker`) |
| Hardware isolation | KVM (Linux), QEMU (macOS) |
| CLI | Python + [Typer](https://typer.tiangolo.com) |
| Config format | YAML (`enclaiv.yaml`) |

---

## Project structure

```
enclaiv/
  cli/            # Python CLI (Typer): init, run, violations, doctor
  proxy/          # Go network proxy + credential proxy
  hardening/      # entrypoint.sh, rootfs stripping, mandatory denies
  templates/      # Agent starter templates
  web/            # Landing page (Next.js)
```

---

## Contributing

The proxy and CLI are both early. There is a lot of room to contribute — network policy improvements, credential provider support, better CLI output, documentation, and tests.

Open an issue to discuss what you want to build before sending a large pull request. For small fixes, a PR is fine directly.

[github.com/earl562/enclaiv/issues](https://github.com/earl562/enclaiv/issues)

---

## License

[Apache 2.0](LICENSE)

"""Enclaiv test agent.

Reads SESSION_TOKEN + CONTROL_PLANE_URL from the environment (injected by the
CLI — never hardcoded), calls the LLM via the control plane, and prints the
response. Also verifies network filtering is working by probing two URLs.
"""

import json
import os
import sys
import urllib.request

SESSION_TOKEN = os.environ.get("SESSION_TOKEN", "")
CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://host.docker.internal:8080")
TASK = os.environ.get("ENCLAIV_TASK", "Say hello in one sentence.")

# ---------------------------------------------------------------------------
# 1. LLM call via control plane
# ---------------------------------------------------------------------------

if not SESSION_TOKEN:
    print("ERROR: SESSION_TOKEN not set — control plane session missing.")
    sys.exit(1)

print(f"Task: {TASK}")
print(f"Control plane: {CONTROL_PLANE_URL}")
print(f"Session token: {SESSION_TOKEN[:16]}...")

payload = json.dumps({
    "messages": [{"role": "user", "content": TASK}],
    "model": "gemini-2.5-flash",
}).encode()

req = urllib.request.Request(
    f"{CONTROL_PLANE_URL}/llm/complete",
    data=payload,
    headers={
        "Authorization": f"Bearer {SESSION_TOKEN}",
        "Content-Type": "application/json",
    },
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    print(f"\nLLM response: {result['content']}")
    print(f"Tokens: {result.get('input_tokens', '?')} in / {result.get('output_tokens', '?')} out")
except Exception as exc:
    print(f"LLM call failed: {exc}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 2. Network filter check (proxy blocks unauthorized domains)
# ---------------------------------------------------------------------------

print("\n--- Network filter check ---")
for url, label in [("http://arxiv.org", "arxiv.org"), ("http://evil.com", "evil.com")]:
    try:
        urllib.request.urlopen(url, timeout=5)
        print(f"{label}: ALLOWED")
    except Exception:
        print(f"{label}: BLOCKED")

print("\nDone.")

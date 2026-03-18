"""
Enclaiv agent template — python-basic starter.

This script runs inside a hardware-isolated Unikraft unikernel VM.

What you can count on:
  - Network access is limited to the domains declared in enclaiv.yaml.
  - The ANTHROPIC_API_KEY is never present in this environment; it is
    injected transparently by the Enclaiv credential proxy.
  - HTTP_PROXY / HTTPS_PROXY are pre-configured — the Anthropic SDK
    picks them up automatically.

Replace the example below with your agent logic.
"""

import anthropic


def main() -> None:
    # The Anthropic client reads the API key from the environment.
    # Inside an Enclaiv VM the key is never set here — the credential
    # proxy injects it after the request leaves the VM.
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello! Introduce yourself briefly."}
        ],
    )

    print(message.content[0].text)


if __name__ == "__main__":
    main()

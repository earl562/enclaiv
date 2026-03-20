"""LLM proxy endpoint — injects credentials and proxies calls to Anthropic or Google.

The agent inside the VM sends requests here with only a SESSION_TOKEN.
The control plane adds the real API key (never inside the VM).

Provider routing:
  gemini-*  →  Google Generative AI
  everything else  →  Anthropic
"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from db import acquire
from models import LLMCompleteRequest, LLMCompleteResponse, MessageRole, SessionStatus

router = APIRouter(prefix="/llm", tags=["llm"])

# ---------------------------------------------------------------------------
# Anthropic config
# ---------------------------------------------------------------------------

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_API_VERSION = "2023-06-01"
_DEFAULT_MODEL = "claude-sonnet-4-6"
_ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Google config
# ---------------------------------------------------------------------------

_GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------


def _is_google(model: str) -> bool:
    return model.startswith("gemini-") or model.startswith("google/")


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def _authenticated_session(request: Request) -> dict:
    """Validate the Bearer token and return the session row."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    token = auth[len("Bearer "):]

    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM sessions WHERE session_token = $1",
            token,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
        )
    if row["status"] != SessionStatus.active.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Session is {row['status']}.",
        )
    return dict(row)


# ---------------------------------------------------------------------------
# Message history
# ---------------------------------------------------------------------------


async def _append_messages(session_id: str, new_messages: list[dict]) -> None:
    import uuid
    sid = uuid.UUID(session_id)
    async with acquire() as conn:
        await conn.execute(
            """
            UPDATE sessions
            SET messages = messages || $1::jsonb
            WHERE id = $2
            """,
            json.dumps(new_messages),
            sid,
        )


# ---------------------------------------------------------------------------
# Anthropic helpers
# ---------------------------------------------------------------------------


def _build_anthropic_request(
    messages: list[dict], model: str, max_tokens: int, stream: bool
) -> dict:
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": stream,
    }


async def _proxy_anthropic(
    messages: list[dict], model: str, max_tokens: int
) -> tuple[str, int, int]:
    if not _ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY is not configured on the control plane.",
        )

    payload = _build_anthropic_request(messages, model, max_tokens, stream=False)
    headers = {
        "x-api-key": _ANTHROPIC_API_KEY,
        "anthropic-version": _ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(_ANTHROPIC_API_URL, json=payload, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Anthropic API error: {resp.text[:500]}",
        )

    data = resp.json()
    content = data["content"][0]["text"]
    usage = data.get("usage", {})
    return content, usage.get("input_tokens", 0), usage.get("output_tokens", 0)


async def _stream_anthropic(
    messages: list[dict], model: str, max_tokens: int
) -> AsyncIterator[bytes]:
    if not _ANTHROPIC_API_KEY:
        yield b"data: {\"error\": \"ANTHROPIC_API_KEY is not configured\"}\n\n"
        return

    payload = _build_anthropic_request(messages, model, max_tokens, stream=True)
    headers = {
        "x-api-key": _ANTHROPIC_API_KEY,
        "anthropic-version": _ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST", _ANTHROPIC_API_URL, json=payload, headers=headers
        ) as resp:
            if resp.status_code != 200:
                error_body = await resp.aread()
                yield b"data: " + error_body + b"\n\n"
                return
            async for chunk in resp.aiter_bytes():
                yield chunk


# ---------------------------------------------------------------------------
# Google helpers
# ---------------------------------------------------------------------------


def _build_google_request(
    messages: list[dict], max_tokens: int, stream: bool
) -> dict:
    """Convert standard messages to Google's `contents` format.

    Google uses role="model" for assistant turns and does not support
    role="system" in contents; system messages are prepended as user turns.
    """
    contents = []
    for msg in messages:
        role = msg["role"]
        if role == MessageRole.system.value:
            # Google doesn't have a system role in contents — prepend as user.
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif role == MessageRole.assistant.value:
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
        else:
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})

    payload: dict = {"contents": contents}
    if not stream:
        payload["generationConfig"] = {"maxOutputTokens": max_tokens}
    return payload


async def _proxy_google(
    messages: list[dict], model: str, max_tokens: int
) -> tuple[str, int, int]:
    if not _GOOGLE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GOOGLE_API_KEY is not configured on the control plane.",
        )

    url = f"{_GOOGLE_API_BASE}/{model}:generateContent?key={_GOOGLE_API_KEY}"
    payload = _build_google_request(messages, max_tokens, stream=False)

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Google API error: {resp.text[:500]}",
        )

    data = resp.json()
    try:
        content = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unexpected Google response shape: {exc}",
        )

    usage = data.get("usageMetadata", {})
    return (
        content,
        usage.get("promptTokenCount", 0),
        usage.get("candidatesTokenCount", 0),
    )


async def _stream_google(
    messages: list[dict], model: str, max_tokens: int
) -> AsyncIterator[bytes]:
    """Stream Google SSE, re-emitting each text chunk as a simple data line."""
    if not _GOOGLE_API_KEY:
        yield b"data: {\"error\": \"GOOGLE_API_KEY is not configured\"}\n\n"
        return

    url = (
        f"{_GOOGLE_API_BASE}/{model}:streamGenerateContent"
        f"?key={_GOOGLE_API_KEY}&alt=sse"
    )
    payload = _build_google_request(messages, max_tokens, stream=True)

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload) as resp:
            if resp.status_code != 200:
                error_body = await resp.aread()
                yield b"data: " + error_body + b"\n\n"
                return
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[len("data:"):].strip()
                if not raw:
                    continue
                try:
                    chunk = json.loads(raw)
                    text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                    yield (
                        b"data: "
                        + json.dumps({"type": "text_delta", "text": text}).encode()
                        + b"\n\n"
                    )
                except (KeyError, IndexError, json.JSONDecodeError):
                    # Forward unrecognised chunks as-is so nothing is silently dropped.
                    yield f"data: {raw}\n\n".encode()

    yield b"data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/complete", response_model=LLMCompleteResponse)
async def llm_complete(
    body: LLMCompleteRequest,
    session: dict = Depends(_authenticated_session),
) -> LLMCompleteResponse | StreamingResponse:
    """Proxy an LLM completion request on behalf of the agent."""
    model = body.model or session.get("model") or _DEFAULT_MODEL
    messages = [{"role": m.role.value, "content": m.content} for m in body.messages]

    use_google = _is_google(model)

    if body.stream:
        await _append_messages(str(session["id"]), messages)
        stream_fn = _stream_google if use_google else _stream_anthropic
        return StreamingResponse(
            stream_fn(messages, model, body.max_tokens),
            media_type="text/event-stream",
        )

    if use_google:
        content, input_tokens, output_tokens = await _proxy_google(
            messages, model, body.max_tokens
        )
    else:
        content, input_tokens, output_tokens = await _proxy_anthropic(
            messages, model, body.max_tokens
        )

    await _append_messages(
        str(session["id"]),
        messages + [{"role": "assistant", "content": content}],
    )

    return LLMCompleteResponse(
        content=content,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

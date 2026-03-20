"""LLM proxy endpoint — injects credentials and proxies calls to Anthropic.

The agent inside the VM sends requests here with only a SESSION_TOKEN.
The control plane adds the real ANTHROPIC_API_KEY (never inside the VM).
"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from db import acquire
from models import LLMCompleteRequest, LLMCompleteResponse, SessionStatus

router = APIRouter(prefix="/llm", tags=["llm"])

# ---------------------------------------------------------------------------
# Supported providers (extend for OpenAI, etc.)
# ---------------------------------------------------------------------------

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_API_VERSION = "2023-06-01"
_DEFAULT_MODEL = "claude-sonnet-4-6"

# Read at startup — never sent to the VM.
_ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


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
# Helpers
# ---------------------------------------------------------------------------


def _build_anthropic_request(
    messages: list[dict],
    model: str,
    max_tokens: int,
    stream: bool,
) -> dict:
    """Build the Anthropic API request body."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": stream,
    }


async def _append_messages(
    session_id: str,
    new_messages: list[dict],
) -> None:
    """Append new messages to the session's message history."""
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
# Non-streaming helper
# ---------------------------------------------------------------------------


async def _proxy_anthropic(
    messages: list[dict],
    model: str,
    max_tokens: int,
) -> tuple[str, int, int]:
    """Call Anthropic synchronously and return (content, input_tokens, output_tokens)."""
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


# ---------------------------------------------------------------------------
# Streaming helper
# ---------------------------------------------------------------------------


async def _stream_anthropic(
    messages: list[dict],
    model: str,
    max_tokens: int,
) -> AsyncIterator[bytes]:
    """Stream SSE bytes from Anthropic, forwarding them to the agent."""
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

    if body.stream:
        # Persist user messages before streaming.
        await _append_messages(str(session["id"]), messages)
        return StreamingResponse(
            _stream_anthropic(messages, model, body.max_tokens),
            media_type="text/event-stream",
        )

    content, input_tokens, output_tokens = await _proxy_anthropic(
        messages, model, body.max_tokens
    )

    # Persist conversation turn.
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

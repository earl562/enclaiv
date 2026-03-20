"""Session lifecycle endpoints."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from db import acquire
from models import (
    CreateSessionRequest,
    SessionResponse,
    SessionStateResponse,
    SessionStatus,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_token() -> str:
    """Return a 32-byte URL-safe token prefixed with 'sess_'."""
    return f"sess_{secrets.token_urlsafe(32)}"


async def _require_session_token(request: Request) -> str:
    """Extract and validate the Bearer token from the Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    return auth[len("Bearer "):]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(body: CreateSessionRequest) -> SessionResponse:
    """Create a new agent session and return a SESSION_TOKEN."""
    session_id = uuid.uuid4()
    token = _generate_token()
    now = datetime.now(timezone.utc)

    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (id, agent_name, task, model, session_token, status, created_at, messages)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            """,
            session_id,
            body.agent_name,
            body.task,
            body.model,
            token,
            SessionStatus.active.value,
            now,
            "[]",
        )

    return SessionResponse(
        id=str(session_id),
        agent_name=body.agent_name,
        task=body.task,
        model=body.model,
        status=SessionStatus.active,
        created_at=now,
        session_token=token,
    )


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(
    session_id: str,
    _token: str = Depends(_require_session_token),
) -> SessionStateResponse:
    """Return the full state of a session, including messages."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session ID.") from exc

    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM sessions WHERE id = $1",
            sid,
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    messages_raw = row["messages"]
    if isinstance(messages_raw, str):
        messages = json.loads(messages_raw)
    else:
        messages = messages_raw

    return SessionStateResponse(
        id=str(row["id"]),
        agent_name=row["agent_name"],
        task=row["task"],
        model=row["model"],
        status=SessionStatus(row["status"]),
        created_at=row["created_at"],
        messages=messages,
    )

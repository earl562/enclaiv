"""Pydantic models for the Enclaiv control plane API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SessionStatus(str, Enum):
    active = "active"
    completed = "completed"
    failed = "failed"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


# ---------------------------------------------------------------------------
# Session models
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=128)
    task: str = Field(..., min_length=1)
    model: str = Field(default="gemini-2.5-flash")


class SessionResponse(BaseModel):
    id: str
    agent_name: str
    task: str
    model: str
    status: SessionStatus
    created_at: datetime
    session_token: str


class SessionStateResponse(BaseModel):
    id: str
    agent_name: str
    task: str
    model: str
    status: SessionStatus
    created_at: datetime
    messages: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# LLM proxy models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: MessageRole
    content: str


class LLMCompleteRequest(BaseModel):
    messages: list[Message]
    model: str | None = None
    max_tokens: int = Field(default=4096, ge=1, le=100_000)
    stream: bool = False


class LLMCompleteResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

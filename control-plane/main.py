"""Enclaiv Control Plane — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import close_db, init_db
from models import HealthResponse
from routes.llm import router as llm_router
from routes.sessions import router as sessions_router


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    await init_db()
    yield
    await close_db()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Enclaiv Control Plane",
    description=(
        "Orchestrates agent VM sessions and proxies LLM calls "
        "so that API credentials never enter the sandbox VM."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)
app.include_router(llm_router)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


@app.get("/healthz", response_model=HealthResponse, tags=["health"])
async def healthz() -> HealthResponse:
    """Liveness probe — always returns 200 if the process is running."""
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))


@app.get("/readyz", response_model=HealthResponse, tags=["health"])
async def readyz() -> HealthResponse:
    """Readiness probe — returns 200 only after the DB pool is initialised."""
    from db import _pool  # noqa: PLC0415

    if _pool is None:
        from fastapi import Response

        return Response(status_code=503)  # type: ignore[return-value]
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))

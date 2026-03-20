"""PostgreSQL connection and session table management (asyncpg)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

# ---------------------------------------------------------------------------
# Connection pool — module-level singleton, initialised at startup.
# ---------------------------------------------------------------------------

_pool: asyncpg.Pool | None = None

_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgres://enclaiv:enclaiv@localhost:5432/enclaiv",
)

# DDL applied once at startup if the table does not exist yet.
_CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id           UUID        PRIMARY KEY,
    agent_name   TEXT        NOT NULL,
    task         TEXT        NOT NULL,
    model        TEXT        NOT NULL DEFAULT 'claude-sonnet-4-6',
    session_token TEXT       NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'active',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    messages     JSONB       NOT NULL DEFAULT '[]'::jsonb
);
"""


async def init_db() -> None:
    """Create the connection pool and apply schema migrations."""
    global _pool
    _pool = await asyncpg.create_pool(_DATABASE_URL, min_size=2, max_size=10)
    async with _pool.acquire() as conn:
        await conn.execute(_CREATE_SESSIONS_TABLE)


async def close_db() -> None:
    """Close the connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Return the active pool; raises if `init_db` has not been called."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised — call init_db() first.")
    return _pool


@asynccontextmanager
async def acquire() -> AsyncGenerator[asyncpg.Connection, None]:
    """Async context manager that yields a connection from the pool."""
    async with get_pool().acquire() as conn:
        yield conn

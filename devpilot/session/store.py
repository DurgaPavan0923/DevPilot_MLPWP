"""SQLite-backed session persistence store."""

import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SessionRecord(BaseModel):
    id: str
    status: str = "INITIALIZED"
    preset: str = "full"
    provider: str = "mock"
    model: str = "mock-model"
    steps: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionStore:
    """Thread-safe persistent SQLite storage for sessions, messages, and execution traces."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    preset TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    steps INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost_usd REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    tool_calls_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS tool_calls (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    output TEXT,
                    duration_ms REAL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS recovery_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    error_type TEXT,
                    signature TEXT,
                    feedback TEXT,
                    abort INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
                CREATE INDEX IF NOT EXISTS idx_recovery_session ON recovery_events(session_id);
            """)

    async def create_session(self, session: SessionRecord) -> None:
        def _insert() -> None:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sessions (id, status, preset, provider, model, steps, total_tokens, total_cost_usd, created_at, updated_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.id,
                        session.status,
                        session.preset,
                        session.provider,
                        session.model,
                        session.steps,
                        session.total_tokens,
                        session.total_cost_usd,
                        session.created_at,
                        session.updated_at,
                        json.dumps(session.metadata),
                    ),
                )

        await asyncio.to_thread(_insert)

    async def get_session(self, session_id: str) -> SessionRecord | None:
        def _get() -> SessionRecord | None:
            with self._get_connection() as conn:
                row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if not row:
                    return None
                return SessionRecord(
                    id=row["id"],
                    status=row["status"],
                    preset=row["preset"],
                    provider=row["provider"],
                    model=row["model"],
                    steps=row["steps"],
                    total_tokens=row["total_tokens"],
                    total_cost_usd=row["total_cost_usd"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    metadata=json.loads(row["metadata_json"] or "{}"),
                )

        return await asyncio.to_thread(_get)

    async def update_session_status(
        self, session_id: str, status: str, steps: int = 0, cost: float = 0.0
    ) -> None:
        def _update() -> None:
            now = datetime.now(UTC).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE sessions
                    SET status = ?, steps = ?, total_cost_usd = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, steps, cost, now, session_id),
                )

        await asyncio.to_thread(_update)

    async def record_message(
        self, session_id: str, role: str, content: str | None, tool_calls_json: str | None = None
    ) -> None:
        def _insert() -> None:
            now = datetime.now(UTC).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO messages (session_id, role, content, tool_calls_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, role, content, tool_calls_json, now),
                )

        await asyncio.to_thread(_insert)

    async def record_tool_call(
        self,
        session_id: str,
        call_id: str,
        tool_name: str,
        arguments_json: str,
        ok: bool,
        output: str,
        duration_ms: float = 0.0,
    ) -> None:
        def _insert() -> None:
            now = datetime.now(UTC).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tool_calls (id, session_id, tool_name, arguments_json, ok, output, duration_ms, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        call_id,
                        session_id,
                        tool_name,
                        arguments_json,
                        1 if ok else 0,
                        output,
                        duration_ms,
                        now,
                    ),
                )

        await asyncio.to_thread(_insert)

    async def record_snapshot(
        self, session_id: str, snapshot_id: str, description: str = ""
    ) -> None:
        def _insert() -> None:
            now = datetime.now(UTC).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO snapshots (id, session_id, description, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (snapshot_id, session_id, description, now),
                )

        await asyncio.to_thread(_insert)

    async def record_recovery_event(
        self,
        session_id: str,
        level: str,
        error_type: str | None,
        signature: str | None,
        feedback: str,
        abort: bool = False,
    ) -> None:
        def _insert() -> None:
            now = datetime.now(UTC).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO recovery_events (session_id, level, error_type, signature, feedback, abort, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        level,
                        error_type,
                        signature,
                        feedback,
                        1 if abort else 0,
                        now,
                    ),
                )

        await asyncio.to_thread(_insert)

    async def update_session_progress(
        self,
        session_id: str,
        status: str,
        steps: int,
        total_tokens: int,
        total_cost_usd: float,
    ) -> None:
        def _update() -> None:
            now = datetime.now(UTC).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE sessions
                    SET status = ?, steps = ?, total_tokens = ?, total_cost_usd = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, steps, total_tokens, total_cost_usd, now, session_id),
                )

        await asyncio.to_thread(_update)

    async def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        def _get() -> list[dict[str, Any]]:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
                    (session_id,),
                ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_get)

    async def get_tool_calls(self, session_id: str) -> list[dict[str, Any]]:
        def _get() -> list[dict[str, Any]]:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY created_at ASC",
                    (session_id,),
                ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_get)

    async def get_snapshots(self, session_id: str) -> list[dict[str, Any]]:
        def _get() -> list[dict[str, Any]]:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM snapshots WHERE session_id = ? ORDER BY created_at ASC",
                    (session_id,),
                ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_get)

    async def get_recovery_events(self, session_id: str) -> list[dict[str, Any]]:
        def _get() -> list[dict[str, Any]]:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM recovery_events WHERE session_id = ? ORDER BY id ASC",
                    (session_id,),
                ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_get)

    async def list_sessions(self, limit: int = 50) -> list[SessionRecord]:
        def _list() -> list[SessionRecord]:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
                records = []
                for row in rows:
                    records.append(
                        SessionRecord(
                            id=row["id"],
                            status=row["status"],
                            preset=row["preset"],
                            provider=row["provider"],
                            model=row["model"],
                            steps=row["steps"],
                            total_tokens=row["total_tokens"],
                            total_cost_usd=row["total_cost_usd"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                            metadata=json.loads(row["metadata_json"] or "{}"),
                        )
                    )
                return records

        return await asyncio.to_thread(_list)

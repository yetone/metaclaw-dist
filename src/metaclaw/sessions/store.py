"""Session persistence using SQLite via SQLModel."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Field, Session as DBSession, SQLModel, create_engine, select


class SessionRecord(SQLModel, table=True):
    """Persistent session record."""

    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_key: str = Field(index=True, unique=True)
    messages_json: str = ""  # JSON-serialized message history
    active_skills_json: str = "[]"
    metadata_json: str = "{}"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class SessionStore:
    """SQLite-backed session persistence."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".metaclaw" / "sessions.db"

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(self._engine)

    def save_session(
        self,
        session_key: str,
        messages: list[dict[str, Any]],
        active_skills: set[str],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save or update a session."""
        with DBSession(self._engine) as db:
            stmt = select(SessionRecord).where(
                SessionRecord.session_key == session_key
            )
            record = db.exec(stmt).first()

            if record is None:
                record = SessionRecord(session_key=session_key)

            record.messages_json = json.dumps(messages)
            record.active_skills_json = json.dumps(list(active_skills))
            record.metadata_json = json.dumps(metadata or {})
            record.updated_at = time.time()

            db.add(record)
            db.commit()

    def load_session(
        self, session_key: str
    ) -> tuple[list[dict[str, Any]], set[str], dict[str, Any]] | None:
        """Load a session. Returns (messages, active_skills, metadata) or None."""
        with DBSession(self._engine) as db:
            stmt = select(SessionRecord).where(
                SessionRecord.session_key == session_key
            )
            record = db.exec(stmt).first()

            if record is None:
                return None

            messages = json.loads(record.messages_json) if record.messages_json else []
            active_skills = set(json.loads(record.active_skills_json))
            metadata = json.loads(record.metadata_json)

            return messages, active_skills, metadata

    def delete_session(self, session_key: str) -> bool:
        """Delete a session. Returns True if it existed."""
        with DBSession(self._engine) as db:
            stmt = select(SessionRecord).where(
                SessionRecord.session_key == session_key
            )
            record = db.exec(stmt).first()
            if record:
                db.delete(record)
                db.commit()
                return True
            return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions with metadata."""
        with DBSession(self._engine) as db:
            records = db.exec(select(SessionRecord)).all()
            return [
                {
                    "session_key": r.session_key,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "message_count": len(
                        json.loads(r.messages_json) if r.messages_json else []
                    ),
                }
                for r in records
            ]

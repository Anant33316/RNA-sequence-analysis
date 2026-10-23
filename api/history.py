"""Optional local analysis history in SQLite (standard library only).

The database lives in data/history.db (override with the RNA_TOC_DB
environment variable; tests use a temporary file). Entries store the
original request so an analysis can be reopened, plus a small summary.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()
MAX_ENTRIES = 500
MAX_PAYLOAD_BYTES = 1_500_000


def db_path() -> Path:
    env = os.environ.get("RNA_TOC_DB")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "history.db"


@contextmanager
def _db():
    """Open, commit on success, always close."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        title TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        payload TEXT NOT NULL)""")
    return conn


def add(kind: str, title: str, summary: dict, payload: dict) -> int | None:
    """Store an entry. Returns its id, or None when the payload is too large
    to be worth storing (the analysis itself still succeeds)."""
    body = json.dumps(payload, ensure_ascii=False)
    if len(body.encode()) > MAX_PAYLOAD_BYTES:
        return None
    with _LOCK, _db() as conn:
        cur = conn.execute("INSERT INTO history (created_at, kind, title, summary, payload) VALUES (?, ?, ?, ?, ?)",
                           (datetime.now(timezone.utc).isoformat(timespec="seconds"), kind, title[:200],
                            json.dumps(summary, ensure_ascii=False), body))
        conn.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
                     (MAX_ENTRIES,))
        return cur.lastrowid


def list_entries(limit: int = 100, kind: str | None = None) -> list[dict]:
    with _LOCK, _db() as conn:
        if kind:
            rows = conn.execute("SELECT id, created_at, kind, title, summary FROM history WHERE kind = ? "
                                "ORDER BY id DESC LIMIT ?", (kind, limit)).fetchall()
        else:
            rows = conn.execute("SELECT id, created_at, kind, title, summary FROM history ORDER BY id DESC LIMIT ?",
                                (limit,)).fetchall()
    return [{"id": r["id"], "created_at": r["created_at"], "kind": r["kind"], "title": r["title"],
             "summary": json.loads(r["summary"])} for r in rows]


def get(entry_id: int) -> dict | None:
    with _LOCK, _db() as conn:
        r = conn.execute("SELECT * FROM history WHERE id = ?", (entry_id,)).fetchone()
    if r is None:
        return None
    return {"id": r["id"], "created_at": r["created_at"], "kind": r["kind"], "title": r["title"],
            "summary": json.loads(r["summary"]), "payload": json.loads(r["payload"])}


def delete(entry_id: int) -> bool:
    with _LOCK, _db() as conn:
        return conn.execute("DELETE FROM history WHERE id = ?", (entry_id,)).rowcount > 0


def clear() -> int:
    with _LOCK, _db() as conn:
        return conn.execute("DELETE FROM history").rowcount

import os
import sqlite3
from typing import Optional


def get_connection() -> sqlite3.Connection:
    path = os.environ.get("DB_PATH", "slack_off.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                channel_id  TEXT NOT NULL,
                created_by  TEXT NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                modified_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)


def save_workspace(name: str, channel_id: str, created_by: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO workspaces (name, channel_id, created_by) VALUES (?, ?, ?)",
            (name, channel_id, created_by),
        )


def get_workspace(name: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM workspaces WHERE name = ?", (name,)
        ).fetchone()

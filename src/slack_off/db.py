import os
import sqlite3
from typing import Optional

from slack_off.workspace import Workspace


def get_connection() -> sqlite3.Connection:
    path = os.environ.get("DB_PATH", "slack_off.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                channel_id    TEXT NOT NULL,
                created_by    TEXT NOT NULL,
                is_active     INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                modified_at   TEXT NOT NULL DEFAULT (datetime('now')),
                sandbox_id    TEXT,
                sandbox_state TEXT,
                UNIQUE(name, created_by)
            )
        """)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns to pre-existing databases that predate them."""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(workspaces)")}
    if "sandbox_id" not in cols:
        conn.execute("ALTER TABLE workspaces ADD COLUMN sandbox_id TEXT")
    if "sandbox_state" not in cols:
        conn.execute("ALTER TABLE workspaces ADD COLUMN sandbox_state TEXT")


def save_workspace(
    name: str,
    channel_id: str,
    created_by: str,
    sandbox_id: Optional[str] = None,
    sandbox_state: Optional[str] = None,
) -> Workspace:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO workspaces (name, channel_id, created_by, sandbox_id, sandbox_state) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, channel_id, created_by, sandbox_id, sandbox_state),
        )
        row = conn.execute(
            "SELECT * FROM workspaces WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return Workspace.from_row(row)


def get_workspace(name: str, created_by: str) -> Optional[Workspace]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM workspaces WHERE name = ? AND created_by = ?", (name, created_by)
        ).fetchone()
    return Workspace.from_row(row) if row else None


def get_workspace_by_channel(channel_id: str) -> Optional[Workspace]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM workspaces WHERE channel_id = ? AND is_active = 1", (channel_id,)
        ).fetchone()
    return Workspace.from_row(row) if row else None


def set_sandbox_state(workspace_id: int, state: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE workspaces SET sandbox_state = ?, modified_at = datetime('now') WHERE id = ?",
            (state, workspace_id),
        )


def list_workspaces(created_by: str) -> list[Workspace]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM workspaces WHERE created_by = ? AND is_active = 1", (created_by,)
        ).fetchall()
    return [Workspace.from_row(row) for row in rows]


def deactivate_workspace(name: str, created_by: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE workspaces SET is_active = 0, modified_at = datetime('now') WHERE name = ? AND created_by = ?",
            (name, created_by),
        )

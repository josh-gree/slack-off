import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Workspace:
    id: int
    name: str
    channel_id: str
    created_by: str
    is_active: bool
    created_at: str
    modified_at: str
    sandbox_id: Optional[str] = None
    sandbox_state: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Workspace":
        return cls(
            id=row["id"],
            name=row["name"],
            channel_id=row["channel_id"],
            created_by=row["created_by"],
            is_active=bool(row["is_active"]),  # SQLite stores 0/1; expose a real bool
            created_at=row["created_at"],
            modified_at=row["modified_at"],
            sandbox_id=row["sandbox_id"],
            sandbox_state=row["sandbox_state"],
        )

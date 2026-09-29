"""Read-only SQLite execution. Every query is guarded first and bound by params."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.sql.guard import check


class Executor:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        # Open strictly read-only; a write attempt raises at the driver level.
        uri = f"file:{Path(self.db_path).resolve()}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only = ON")
        return con

    def run(self, sql: str, params: dict | None = None) -> tuple[list[dict], int]:
        check(sql)
        with self._connect() as con:
            cur = con.execute(sql, params or {})
            rows = [dict(r) for r in cur.fetchall()]
        return rows, len(rows)

    def scalar(self, sql: str, params: dict | None = None):
        rows, _ = self.run(sql, params)
        if not rows:
            return None
        return next(iter(rows[0].values()))

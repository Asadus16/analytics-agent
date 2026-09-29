"""Query log: every answered question is recorded with the exact SQL and value.

This is the 'show your work' audit — a client can trace any number back to the
metric, the parameters, the SQL that ran and the row count behind it.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.metrics.layer import Answer


class QueryLog:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS query_log (
                    audit_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    question TEXT,
                    metric TEXT NOT NULL,
                    params TEXT NOT NULL,
                    value TEXT,
                    source TEXT NOT NULL,
                    row_count INTEGER,
                    narrative TEXT
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def record(self, answer: Answer, question: str, narrative: str) -> str:
        audit_id = str(uuid.uuid4())
        value = answer.value if answer.value is not None else json.dumps(answer.grouped_rows)
        with self._connect() as con:
            con.execute(
                "INSERT INTO query_log VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    audit_id, datetime.now(timezone.utc).isoformat(), question,
                    answer.metric, json.dumps(answer.params), str(value),
                    answer.source, answer.row_count, narrative,
                ),
            )
        return audit_id

    def get(self, audit_id: str) -> dict | None:
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT * FROM query_log WHERE audit_id=?", (audit_id,)
            ).fetchone()
            return dict(row) if row else None

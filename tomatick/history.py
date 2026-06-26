"""Timestamped event history backed by SQLite.

Stored at ``~/Library/Application Support/Tomatick/history.db``. No macOS
imports here so the store is unit-testable anywhere.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .settings import support_dir

# Recognized event actions (free-form strings are allowed, these document intent).
ACTIONS = {
    "started",
    "paused",
    "resumed",
    "completed",
    "stopped",
    "reset",
    "phase_change",
    "lap",
    "alarm_fired",
    "alarm_dismissed",
    "snoozed",
}


def db_path() -> Path:
    return support_dir() / "history.db"


class History:
    """A thin SQLite wrapper for appending and querying timestamped events."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else db_path()
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ts           TEXT    NOT NULL,
                kind         TEXT    NOT NULL,
                label        TEXT,
                action       TEXT    NOT NULL,
                details_json TEXT,
                duration_s   INTEGER
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
        self._conn.commit()

    def log_event(
        self,
        kind: str,
        action: str,
        label: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        duration_s: Optional[int] = None,
        ts: Optional[datetime] = None,
    ) -> int:
        """Append an event. Returns the new row id.

        ``ts`` defaults to now; pass an explicit value in tests for determinism.
        """
        when = (ts or datetime.now()).isoformat(timespec="seconds")
        cur = self._conn.execute(
            "INSERT INTO events (ts, kind, label, action, details_json, duration_s) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                when,
                kind,
                label,
                action,
                json.dumps(details) if details else None,
                duration_s,
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def recent(self, limit: int = 10) -> List[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        )
        return cur.fetchall()

    def all(self) -> List[sqlite3.Row]:
        return self._conn.execute("SELECT * FROM events ORDER BY id ASC").fetchall()

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def clear(self) -> None:
        self._conn.execute("DELETE FROM events")
        self._conn.commit()

    # Export ---------------------------------------------------------------
    def export_csv(self, path: str | Path) -> Path:
        rows = self.all()
        out = Path(path)
        with out.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["id", "ts", "kind", "label", "action", "details_json", "duration_s"]
            )
            for r in rows:
                writer.writerow(
                    [r["id"], r["ts"], r["kind"], r["label"], r["action"],
                     r["details_json"], r["duration_s"]]
                )
        return out

    def export_json(self, path: str | Path) -> Path:
        rows = [dict(r) for r in self.all()]
        out = Path(path)
        out.write_text(json.dumps(rows, indent=2))
        return out

    def close(self) -> None:
        self._conn.close()

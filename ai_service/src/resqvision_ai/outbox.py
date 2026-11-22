"""Small SQLite outbox for safe retry and restart recovery of event submissions."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .contracts import DetectionEventPayload
from .errors import OutboxConflict


class SQLiteEventOutbox:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS pending_detection_events (
                    source_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error_code TEXT,
                    queued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (source_id, event_id)
                )"""
            )
        if os.name != "nt":
            self.path.chmod(0o600)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5.0)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def enqueue(self, payload: DetectionEventPayload) -> None:
        encoded = json.dumps(payload.to_mapping(), sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO pending_detection_events "
                "(source_id, event_id, payload_json) VALUES (?, ?, ?)",
                (str(payload.video_source_id), payload.external_event_id, encoded),
            )
            row = connection.execute(
                "SELECT payload_json FROM pending_detection_events "
                "WHERE source_id = ? AND event_id = ?",
                (str(payload.video_source_id), payload.external_event_id),
            ).fetchone()
            if row[0] != encoded:
                raise OutboxConflict("An event ID is already queued with different content.")

    def pending(self, limit: int = 100) -> list[DetectionEventPayload]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM pending_detection_events "
                "ORDER BY queued_at, event_id LIMIT ?",
                (limit,),
            ).fetchall()
        return [DetectionEventPayload.from_mapping(json.loads(row[0])) for row in rows]

    def record_failure(self, payload: DetectionEventPayload, safe_error_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """UPDATE pending_detection_events
                   SET attempts = attempts + 1, last_error_code = ?
                   WHERE source_id = ? AND event_id = ?""",
                (safe_error_code[:64], str(payload.video_source_id), payload.external_event_id),
            )

    def mark_delivered(self, payload: DetectionEventPayload) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM pending_detection_events WHERE source_id = ? AND event_id = ?",
                (str(payload.video_source_id), payload.external_event_id),
            )

    def pending_count(self) -> int:
        with self._connect() as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM pending_detection_events").fetchone()[0]
            )

    def is_writable(self) -> bool:
        connection = sqlite3.connect(self.path, timeout=5.0)
        try:
            connection.execute("SELECT 1 FROM pending_detection_events LIMIT 1")
            connection.execute("BEGIN IMMEDIATE")
            connection.rollback()
            return True
        except sqlite3.Error:
            return False
        finally:
            connection.close()

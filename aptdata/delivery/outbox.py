"""Durable Delivery Outbox — SQLite-backed message queue for reliable event delivery.

Why this exists:
- Ensures at-least-once delivery semantics without depending on an
  external message broker. The outbox pattern guarantees that events
  are not lost before the delivery layer can send them.
- Idempotency by (event_id, channel) prevents duplicate messages even
  if the producer retries.
- Transactional claim-and-attempts-increment enables safe, concurrent
  worker processes without double-delivery.
- Sanitized error storage allows observability without leaking secrets.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from aptdata.events.models import FlowEvent


class OutboxStatus(str, Enum):
    """Lifecycle states of an outbox message."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class OutboxMessage:
    """A single row in the outbox, representing one delivery attempt for one channel.

    Attributes are named to be self-explanatory to someone unfamiliar with
    the codebase:
      * message_id — unique primary key for this delivery attempt.
      * event_id — the FlowEvent's event_id (note: not a foreign key, a trace id).
      * channel — which delivery channel this message targets.
      * status — one of pending/sent/failed.
      * attempts — how many times this message has been claimed for delivery.
      * payload_json — the serialized FlowEvent as a JSON string.
      * created_at — when the outbox row was created.
      * sent_at — when the delivery was confirmed (None until sent).
      * last_error — sanitized error from the last failed delivery attempt.
    """

    def __init__(
        self,
        message_id: str,
        event_id: str,
        channel: str,
        status: OutboxStatus,
        attempts: int,
        payload_json: str,
        created_at: datetime,
        sent_at: datetime | None = None,
        last_error: str | None = None,
    ) -> None:
        self.message_id = message_id
        self.event_id = event_id
        self.channel = channel
        self.status = status
        self.attempts = attempts
        self.payload_json = payload_json
        self.created_at = created_at
        self.sent_at = sent_at
        self.last_error = last_error

    def __repr__(self) -> str:
        return (
            f"OutboxMessage("
            f"message_id={self.message_id!r}, "
            f"event_id={self.event_id!r}, "
            f"channel={self.channel!r}, "
            f"status={self.status.value!r}, "
            f"attempts={self.attempts})"
        )


class DurableOutbox:
    """SQLite-backed durable outbox for reliable event delivery.

    Usage::

        outbox = DurableOutbox(db_path="/path/to/outbox.db")
        outbox.enqueue(event, channel="telegram")
        pending = outbox.claim_pending(limit=10)
        for msg in pending:
            try:
                # ... deliver msg.payload_json to channel ...
                outbox.mark_sent(msg.message_id)
            except Exception as e:
                outbox.mark_failed(msg.message_id, str(e))
        outbox.close()

    Thread-safety note: SQLite in WAL mode supports concurrent reads
    and serialized writes. For multi-process workers, each process
    should create its own DurableOutbox instance pointing to the same
    database file.
    """

    # Maximum length of a stored error message — prevents abuse and
    # ensures no tokens/secrets are stored in full.
    _MAX_ERROR_LENGTH: int = 512

    def __init__(self, db_path: str) -> None:
        """Initialize the outbox database.

        Creates the table and indexes if they don't exist. Uses WAL mode
        for better concurrent read performance.
        """
        self._db_path = str(Path(db_path).resolve())
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the outbox table and its indexes if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS outbox_messages (
                message_id     TEXT PRIMARY KEY,
                event_id       TEXT NOT NULL,
                channel        TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending', 'sent', 'failed')),
                attempts       INTEGER NOT NULL DEFAULT 0,
                payload_json   TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                sent_at        TEXT,
                last_error     TEXT
            );

            -- Idempotency: only one pending/failed row per (event_id, channel).
            CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_event_channel
                ON outbox_messages(event_id, channel);

            -- Fast lookup of claimable messages.
            CREATE INDEX IF NOT EXISTS idx_outbox_claimable
                ON outbox_messages(status, attempts);
        """)
        self._conn.commit()

    def enqueue(self, event: FlowEvent, channel: str) -> OutboxMessage:
        """Insert or return the existing outbox message for this event+channel.

        If a row with the same (event_id, channel) already exists it is
        returned unchanged — the enqueue is idempotent.

        The FlowEvent is serialized to JSON and stored as payload_json.
        """
        event_id_str = str(event.event_id)
        payload = event.model_dump_json()
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()

        cursor = self._conn.execute(
            """INSERT OR IGNORE INTO outbox_messages
               (message_id, event_id, channel, status, attempts,
                payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid4()),
                event_id_str,
                channel,
                OutboxStatus.PENDING.value,
                0,
                payload,
                now_str,
            ),
        )
        self._conn.commit()

        # If INSERT IGNORE took effect (row already exists), fetch the
        # existing row instead.
        if cursor.rowcount == 0:
            return self._fetch_by_event_channel(event_id_str, channel)

        return self._fetch_by_event_channel(event_id_str, channel)

    def _fetch_by_event_channel(self, event_id: str, channel: str) -> OutboxMessage:
        """Fetch a single outbox row by (event_id, channel)."""
        row = self._conn.execute(
            "SELECT * FROM outbox_messages WHERE event_id = ? AND channel = ?",
            (event_id, channel),
        ).fetchone()
        if row is None:
            raise RuntimeError(
                f"Outbox row not found for event_id={event_id}, channel={channel}"
            )
        return self._row_to_message(row)

    def _fetch_one(self, message_id: str) -> OutboxMessage:
        """Fetch a single outbox row by primary key.

        Exposed for test inspection.
        """
        row = self._conn.execute(
            "SELECT * FROM outbox_messages WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Outbox message {message_id} not found")
        return self._row_to_message(row)

    def claim_pending(self, limit: int = 10) -> list[OutboxMessage]:
        """Claim up to *limit* pending or failed messages for delivery.

        This is a transactional claim that:
        1. Selects rows with status IN ('pending', 'failed').
        2. Increments their attempts counter.
        3. Returns the updated rows.

        Only callers that receive a row should attempt delivery — the
        attempt count increase acts as a lease.
        """
        self._conn.execute("BEGIN IMMEDIATE;")
        try:
            rows = self._conn.execute(
                """SELECT rowid, * FROM outbox_messages
                   WHERE status IN ('pending', 'failed')
                   LIMIT ?""",
                (limit,),
            ).fetchall()

            if not rows:
                self._conn.execute("COMMIT;")
                return []

            rowids = [r["rowid"] for r in rows]
            placeholders = ",".join("?" for _ in rowids)
            self._conn.execute(
                f"""UPDATE outbox_messages
                    SET attempts = attempts + 1
                    WHERE rowid IN ({placeholders})""",
                rowids,
            )
            self._conn.commit()

            # Re-fetch updated rows
            updated = self._conn.execute(
                f"""SELECT * FROM outbox_messages
                    WHERE rowid IN ({placeholders})""",
                rowids,
            ).fetchall()

            return [self._row_to_message(r) for r in updated]
        except Exception:
            self._conn.execute("ROLLBACK;")
            raise

    def mark_sent(self, message_id: str) -> None:
        """Mark a message as successfully sent.

        Idempotent — calling mark_sent on an already-sent message is a
        no-op (the sent_at timestamp is not overwritten).
        """
        now_str = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """UPDATE outbox_messages
               SET status = ?,
                   sent_at = COALESCE(sent_at, ?)
               WHERE message_id = ? AND status != ?""",
            (OutboxStatus.SENT.value, now_str, message_id, OutboxStatus.SENT.value),
        )
        self._conn.commit()

    def mark_failed(self, message_id: str, error: str) -> None:
        """Mark a message as failed with a sanitized error string.

        The error string is truncated to _MAX_ERROR_LENGTH characters
        to prevent storing secrets, tokens, or excessively large error
        payloads.
        """
        sanitized = error[: self._MAX_ERROR_LENGTH]
        self._conn.execute(
            """UPDATE outbox_messages
               SET status = ?, last_error = ?
               WHERE message_id = ?""",
            (OutboxStatus.FAILED.value, sanitized, message_id),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection. Idempotent."""
        if self._conn:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def __enter__(self) -> DurableOutbox:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> OutboxMessage:
        """Convert a sqlite3.Row to an OutboxMessage, parsing datetime fields."""
        created_at = datetime.fromisoformat(row["created_at"])
        sent_at: datetime | None = (
            datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None
        )
        return OutboxMessage(
            message_id=row["message_id"],
            event_id=row["event_id"],
            channel=row["channel"],
            status=OutboxStatus(row["status"]),
            attempts=row["attempts"],
            payload_json=row["payload_json"],
            created_at=created_at,
            sent_at=sent_at,
            last_error=row["last_error"],
        )

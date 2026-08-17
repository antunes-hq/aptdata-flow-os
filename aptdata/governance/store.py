"""SQLite-backed append-only store for trusted squad governance records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from aptdata.events.models import FlowEvent
from aptdata.governance.models import (
    ContextPacket,
    EvidenceRecord,
    JudgeResult,
    MaestroDecision,
    SquadDefinition,
    WorkPacket,
)

Record = TypeVar(
    "Record",
    ContextPacket,
    SquadDefinition,
    WorkPacket,
    EvidenceRecord,
    JudgeResult,
    MaestroDecision,
)

_TABLE_BY_TYPE: dict[type[Any], str] = {
    ContextPacket: "context_packets",
    SquadDefinition: "squad_definitions",
    WorkPacket: "work_packets",
    EvidenceRecord: "evidence_records",
    JudgeResult: "judge_results",
    MaestroDecision: "maestro_decisions",
}


class GovernanceStore:
    """Persist versioned governance records without mutating prior rows.

    The store is intentionally separate from aptdata's execution state and from
    project data stores. Each write is one immutable JSON document keyed by the
    record's public id and version.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS governance_records (
                record_id TEXT NOT NULL,
                record_type TEXT NOT NULL,
                version INTEGER NOT NULL,
                work_packet_id TEXT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (record_type, record_id, version)
            );
            CREATE INDEX IF NOT EXISTS idx_governance_work_packet
                ON governance_records(work_packet_id, created_at);
            CREATE TABLE IF NOT EXISTS flow_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_flow_events_run
                ON flow_events(run_id, created_at, event_id);
            """
        )
        self._connection.commit()

    def _insert(self, record: Record) -> None:
        """Insert one record inside the caller's transaction."""
        record_type = type(record)
        table_name = _TABLE_BY_TYPE.get(record_type)
        if table_name is None:
            raise TypeError(f"unsupported governance record: {record_type!r}")
        payload = record.model_dump(mode="json")
        record_id = str(payload["id"])
        version = int(payload.get("version", 1))
        work_packet_id = payload.get("work_packet_id")
        if record_type is WorkPacket:
            work_packet_id = record_id
        try:
            self._connection.execute(
                """
                INSERT INTO governance_records
                    (record_id, record_type, version, work_packet_id, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    table_name,
                    version,
                    work_packet_id,
                    json.dumps(payload, sort_keys=True),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"governance record already exists: {table_name}/{record_id}/v{version}"
            ) from exc

    def append(self, record: Record) -> None:
        """Append a validated record; duplicate identity/version is rejected."""
        try:
            self._insert(record)
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def append_many(self, records: Iterable[Record]) -> None:
        """Append multiple records atomically."""
        try:
            for record in records:
                self._insert(record)
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def get(
        self, record_type: type[Record], record_id: str, version: int | None = None
    ) -> Record | None:
        """Load one typed record, selecting the newest version by default."""
        table_name = _TABLE_BY_TYPE.get(record_type)
        if table_name is None:
            raise TypeError(f"unsupported governance record: {record_type!r}")
        query = (
            "SELECT payload FROM governance_records "
            "WHERE record_type = ? AND record_id = ?"
        )
        params: list[Any] = [table_name, record_id]
        if version is not None:
            query += " AND version = ?"
            params.append(version)
        else:
            query += " ORDER BY version DESC LIMIT 1"
        row = self._connection.execute(query, params).fetchone()
        return record_type.model_validate(json.loads(row["payload"])) if row else None

    def for_work_packet(self, work_packet_id: str) -> list[dict[str, Any]]:
        """Return all records linked to a WorkPacket, oldest first."""
        rows = self._connection.execute(
            """
            SELECT record_id, record_type, version, payload, created_at
            FROM governance_records
            WHERE work_packet_id = ?
            ORDER BY created_at, record_type, record_id, version
            """,
            (work_packet_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        """Return the number of immutable records."""
        return int(
            self._connection.execute(
                "SELECT COUNT(*) AS count FROM governance_records"
            ).fetchone()["count"]
        )

    def append_event(self, event: FlowEvent) -> None:
        """Append one immutable FlowEvent, rejecting duplicate event IDs."""
        payload = event.model_dump(mode="json")
        try:
            self._connection.execute(
                """
                INSERT INTO flow_events (
                    event_id, run_id, event_type, payload, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    event.run_id,
                    event.event_type,
                    json.dumps(payload, sort_keys=True),
                    event.created_at.isoformat(),
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            self._connection.rollback()
            raise ValueError(f"event already exists: {event.event_id}") from exc

    def get_event(self, event_id: object) -> FlowEvent | None:
        """Load one immutable FlowEvent by UUID."""
        row = self._connection.execute(
            "SELECT payload FROM flow_events WHERE event_id = ?",
            (str(event_id),),
        ).fetchone()
        return FlowEvent.model_validate(json.loads(row["payload"])) if row else None

    def for_run(self, run_id: str) -> list[FlowEvent]:
        """Load all FlowEvents for one run in creation order."""
        rows = self._connection.execute(
            """
            SELECT payload FROM flow_events
            WHERE run_id = ?
            ORDER BY created_at, event_id
            """,
            (run_id,),
        ).fetchall()
        return [FlowEvent.model_validate(json.loads(row["payload"])) for row in rows]

    def events(self) -> list[FlowEvent]:
        """Load all FlowEvents in creation order."""
        rows = self._connection.execute(
            "SELECT payload FROM flow_events ORDER BY created_at, event_id"
        ).fetchall()
        return [FlowEvent.model_validate(json.loads(row["payload"])) for row in rows]

    def close(self) -> None:
        """Close the SQLite connection."""
        self._connection.close()

    def __enter__(self) -> GovernanceStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


__all__ = ["GovernanceStore"]

"""Event store próprio do aptdata (SQLite, append-only).

Persistência local dos eventos de observabilidade — decisões de roteamento,
dispatches, respostas, permissões, subida de apps — sem exigir collector
externo. É a fonte que CLI (``aptdata obs``), viz e TUI leem.

Schema: ``events(id, ts, run_id, trace_id, kind, agent_id, payload)``,
payload serializado como JSON.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

ENV_DB = "APTDATA_OBS_DB"
DEFAULT_DB = "~/.aptdata/events.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       REAL NOT NULL,
    run_id   TEXT,
    trace_id TEXT,
    kind     TEXT NOT NULL,
    agent_id TEXT,
    payload  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events (kind);
CREATE INDEX IF NOT EXISTS idx_events_run ON events (run_id);
"""


def resolve_db_path(path: str | Path | None = None) -> Path:
    """Resolve o caminho do banco: argumento > $APTDATA_OBS_DB > default."""
    candidate = path or os.getenv(ENV_DB) or DEFAULT_DB
    return Path(candidate).expanduser()


class ObservabilityStore:
    """Sink SQLite thread-safe (o servidor viz é thread-per-request)."""

    def __init__(self, path: str | Path | None = None):
        self.path = resolve_db_path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- write ---------------------------------------------------------------

    def append(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
        trace_id: str | None = None,
        agent_id: str | None = None,
        ts: float | None = None,
    ) -> None:
        body = json.dumps(payload or {}, ensure_ascii=False, default=str)
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (ts, run_id, trace_id, kind, agent_id, payload)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    ts if ts is not None else time.time(),
                    run_id,
                    trace_id,
                    kind,
                    agent_id,
                    body,
                ),
            )
            self._conn.commit()

    # -- read ----------------------------------------------------------------

    def tail(
        self,
        limit: int = 50,
        *,
        kind: str | None = None,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Últimos *limit* eventos (ordem cronológica), com filtros opcionais."""
        query = "SELECT ts, run_id, trace_id, kind, agent_id, payload FROM events"
        clauses, params = [], []
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        events = [
            {
                "ts": ts,
                "run_id": rid,
                "trace_id": tid,
                "kind": k,
                "agent_id": aid,
                "payload": json.loads(body),
            }
            for ts, rid, tid, k, aid, body in rows
        ]
        events.reverse()
        return events

    def last_id(self) -> int:
        """Maior id já gravado (0 se vazio) — cursor para :meth:`since`."""
        with self._lock:
            row = self._conn.execute("SELECT MAX(id) FROM events").fetchone()
        return row[0] or 0

    def since(
        self, last_id: int = 0, limit: int = 100
    ) -> tuple[int, list[dict[str, Any]]]:
        """Eventos com ``id > last_id`` (ordem cronológica) + novo cursor.

        Base do streaming incremental (SSE do viz, refresh da TUI): o
        chamador guarda o cursor devolvido e repete a chamada.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, ts, run_id, trace_id, kind, agent_id, payload"
                " FROM events WHERE id > ? ORDER BY id ASC LIMIT ?",
                (last_id, limit),
            ).fetchall()
        events = [
            {
                "ts": ts,
                "run_id": rid,
                "trace_id": tid,
                "kind": kind,
                "agent_id": aid,
                "payload": json.loads(body),
            }
            for _, ts, rid, tid, kind, aid, body in rows
        ]
        cursor = rows[-1][0] if rows else last_id
        return cursor, events

    def summary(self) -> dict[str, Any]:
        """Resumo agregado: totais por kind, dispatches ok/erro, latência média."""
        with self._lock:
            by_kind = dict(
                self._conn.execute(
                    "SELECT kind, COUNT(*) FROM events GROUP BY kind"
                ).fetchall()
            )
            last_ts = self._conn.execute("SELECT MAX(ts) FROM events").fetchone()[0]
            responses = [
                json.loads(body)
                for (body,) in self._conn.execute(
                    "SELECT payload FROM events WHERE kind = 'agent.response'"
                ).fetchall()
            ]
            decisions = [
                json.loads(body)
                for (body,) in self._conn.execute(
                    "SELECT payload FROM events WHERE kind = 'routing.decision'"
                ).fetchall()
            ]

        ok = sum(1 for r in responses if r.get("ok"))
        latencies = [r["latency_ms"] for r in responses if "latency_ms" in r]
        decisions_by_mode: dict[str, int] = {}
        for d in decisions:
            mode = d.get("mode") or "unknown"
            decisions_by_mode[mode] = decisions_by_mode.get(mode, 0) + 1

        return {
            "available": True,
            "db": str(self.path),
            "total_events": sum(by_kind.values()),
            "by_kind": by_kind,
            "decisions_by_mode": decisions_by_mode,
            "dispatches": {
                "total": len(responses),
                "ok": ok,
                "error": len(responses) - ok,
                "avg_latency_ms": (
                    round(sum(latencies) / len(latencies), 3) if latencies else None
                ),
            },
            "last_event_ts": last_ts,
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()

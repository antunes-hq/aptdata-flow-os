"""Persistent workflow execution state backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateBackend:
    """Simple JSON-on-disk backend used for checkpointing workflow state."""

    def __init__(self, base_dir: str | Path = ".aptdata_state") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: str, state: dict[str, Any]) -> None:
        """Persist *state* for *run_id*."""
        path = self.base_dir / f"{run_id}.json"
        path.write_text(json.dumps(state, ensure_ascii=False, default=str), encoding="utf-8")

    def load(self, run_id: str) -> dict[str, Any]:
        """Load state for *run_id*."""
        path = self.base_dir / f"{run_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

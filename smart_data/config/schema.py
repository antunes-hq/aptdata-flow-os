"""JSON Schema utilities for declarative smart-data configs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from smart_data.config.parser import ParsedConfig


def export_domain_schema() -> dict[str, Any]:
    """Export JSON Schema for the full declarative config domain."""
    return TypeAdapter(ParsedConfig).json_schema()


def write_domain_schema(output: str | Path) -> Path:
    """Write the domain JSON Schema to *output*."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(export_domain_schema(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path

"""JSON Schema utilities for declarative aptdata configs (ADR-002 §2.2).

Three versioned schemas live under ``.aptdata/schemas/`` and are validated by
``aptdata doctor`` (via ``check-jsonschema``):

* ``config.json``  — :class:`~aptdata.config.parser.ParsedConfig` (pipelines).
* ``agents.json``  — :class:`AgentsFile` (``agents:`` + ``skills:`` + ``routing:``).
* ``system.json``  — :class:`SystemManifest` (the ``aptdata.yaml`` envelope).

The schemas are generated from the same pydantic models the loaders use,
so the contract is always a single source of truth — never hand-written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, TypeAdapter

from aptdata.agents.base import AgentSpec
from aptdata.agents.conversation import DecisionPolicy
from aptdata.agents.router import Skill
from aptdata.config.parser import ParsedConfig

# ---------------------------------------------------------------------------
# Agents file envelope (.aptdata/agents.yaml)
# ---------------------------------------------------------------------------


class AgentsFile(BaseModel):
    """Top-level structure of ``.aptdata/agents.yaml``.

    Composes the agent registry (``agents:``), the skill routing table
    (``skills:``) and the routing policy thresholds (``routing:``). The JSON
    Schema generated from this model is what ``aptdata doctor`` validates
    the file against.
    """

    model_config = {"extra": "forbid"}

    agents: dict[str, AgentSpec] = Field(default_factory=dict)
    skills: list[Skill] = Field(default_factory=list)
    routing: DecisionPolicy = Field(default_factory=DecisionPolicy)
    transports: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# System manifest (.aptdata/system.yaml)
# ---------------------------------------------------------------------------


class SystemManifest(BaseModel):
    """Top-level structure of ``.aptdata/system.yaml``.

    Replaces the legacy root-level ``aptdata.yaml``. Carries the system id
    and the flows declared for it; the ``imports`` list is preserved from
    the legacy :class:`~aptdata.core.yaml_builder.YamlSystemBuilder` for
    custom component loading.
    """

    model_config = {"extra": "forbid"}

    system: dict[str, Any] = Field(
        default_factory=lambda: {"id": "default"},
        description="System block: id, flows, telemetry, etc.",
    )
    imports: list[str] = Field(
        default_factory=list,
        description="Custom Python modules to load so their components register.",
    )


# ---------------------------------------------------------------------------
# Schema generation
# ---------------------------------------------------------------------------


def export_config_schema() -> dict[str, Any]:
    """Export JSON Schema for ``.aptdata/config.yaml`` (ParsedConfig)."""
    return TypeAdapter(ParsedConfig).json_schema()


def export_agents_schema() -> dict[str, Any]:
    """Export JSON Schema for ``.aptdata/agents.yaml`` (AgentsFile)."""
    return TypeAdapter(AgentsFile).json_schema()


def export_system_schema() -> dict[str, Any]:
    """Export JSON Schema for ``.aptdata/system.yaml`` (SystemManifest)."""
    return TypeAdapter(SystemManifest).json_schema()


def export_domain_schema() -> dict[str, Any]:
    """Export JSON Schema for the full declarative config domain.

    Kept for backwards-compat with the legacy ``aptdata schema export``
    command (which targets ``.aptdata/config.yaml``).
    """
    return export_config_schema()


def write_schema(kind: str, output: str | Path) -> Path:
    """Write one of the three schemas (``config``/``agents``/``system``)."""
    schemas = {
        "config": export_config_schema,
        "agents": export_agents_schema,
        "system": export_system_schema,
    }
    if kind not in schemas:
        raise ValueError(
            f"Unknown schema kind {kind!r}. Choose one of: {sorted(schemas)}"
        )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schemas[kind](), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def write_domain_schema(output: str | Path) -> Path:
    """Write the config-domain JSON Schema to *output* (legacy alias)."""
    return write_schema("config", output)


def write_all_schemas(schemas_dir: str | Path) -> dict[str, Path]:
    """Write all three schemas into *schemas_dir* and return their paths."""
    schemas_dir = Path(schemas_dir)
    schemas_dir.mkdir(parents=True, exist_ok=True)
    return {
        kind: write_schema(kind, schemas_dir / f"{kind}.json")
        for kind in ("config", "agents", "system")
    }


__all__ = [
    "AgentsFile",
    "SystemManifest",
    "export_agents_schema",
    "export_config_schema",
    "export_domain_schema",
    "export_system_schema",
    "write_all_schemas",
    "write_domain_schema",
    "write_schema",
]

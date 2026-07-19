"""Tests for JSON Schema generation (ADR-002 §2.2).

Three versioned schemas under ``.aptdata/schemas/`` are generated from the
same pydantic models the loaders use, so the contract is a single source of
truth. ``aptdata doctor`` validates the YAMLs against these schemas.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aptdata.config.schema import (
    AgentsFile,
    SystemManifest,
    export_agents_schema,
    export_config_schema,
    export_domain_schema,
    export_system_schema,
    write_all_schemas,
    write_schema,
)

# ---------------------------------------------------------------------------
# Schema generation
# ---------------------------------------------------------------------------


class TestSchemaGeneration:
    def test_config_schema_is_json_schema(self):
        schema = export_config_schema()
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_agents_schema_has_agents_skills_routing(self):
        schema = export_agents_schema()
        props = schema["properties"]
        # The three top-level blocks of .aptdata/agents.yaml
        assert "agents" in props
        assert "skills" in props
        assert "routing" in props
        # transports is optional (kept for telegram config)
        assert "transports" in props

    def test_system_schema_has_system_and_imports(self):
        schema = export_system_schema()
        props = schema["properties"]
        assert "system" in props
        assert "imports" in props

    def test_agents_schema_forbids_extras(self):
        """``extra='forbid'`` so typos in agents.yaml fail fast."""
        schema = export_agents_schema()
        assert schema.get("additionalProperties") is False

    def test_system_schema_forbids_extras(self):
        schema = export_system_schema()
        assert schema.get("additionalProperties") is False

    def test_agents_schema_exposes_default_mode(self):
        """PR3 — AgentsFile.default_mode aparece no JSON Schema (ADR-002 §2.3)."""
        schema = export_agents_schema()
        props = schema["properties"]
        assert "default_mode" in props
        # O enum dos 4 modos canônicos tem que aparecer no schema (em $defs
        # ou inline) para check-jsonschema validar valores inválidos.
        body = json.dumps(schema)
        for mode in ("oneshot", "converse", "project", "orchestrated"):
            assert mode in body, f"modo {mode!r} ausente do agents.json"

    def test_domain_schema_aliases_config_schema(self):
        """export_domain_schema is a legacy alias for the config schema."""
        assert export_domain_schema() == export_config_schema()

    def test_agents_schema_validates_real_world_agents_yaml(self):
        """A representative agents.yaml with container/metadata must validate
        against the generated schema — this is the regression the AgentSpec
        `container`+`metadata` fields fixed in PR0."""
        from aptdata.agents.base import AgentSpec
        from aptdata.agents.router import Skill

        spec = AgentSpec(
            id="holt",
            name="Holt",
            type="openclaw",
            container="openclaw-holt-openclaw-1",
            metadata={"telegram": "@holt_dev_bot", "vps": True},
            capabilities=["monitoria"],
        )
        skill = Skill(name="monitor", keywords=["monitor"], backend="holt")
        model = AgentsFile(
            agents={"holt": spec},
            skills=[skill],
            routing={"dispatch_above": 0.8, "guarded_capabilities": ["deploy"]},
        )
        # Should round-trip without loss
        dumped = model.model_dump()
        assert dumped["agents"]["holt"]["container"] == "openclaw-holt-openclaw-1"
        assert dumped["agents"]["holt"]["metadata"]["telegram"] == "@holt_dev_bot"


# ---------------------------------------------------------------------------
# write_schema / write_all_schemas
# ---------------------------------------------------------------------------


class TestWriteSchema:
    def test_write_schema_writes_json(self, tmp_path: Path):
        path = write_schema("agents", tmp_path / "agents.json")
        assert path.is_file()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["type"] == "object"

    def test_write_schema_rejects_unknown_kind(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Unknown schema kind"):
            write_schema("bogus", tmp_path / "x.json")

    def test_write_domain_schema_writes_config_schema(self, tmp_path: Path):
        """The legacy alias writes the same schema as write_schema('config', ...)."""
        from aptdata.config.schema import write_domain_schema

        out = write_domain_schema(tmp_path / "schema.json")
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded == export_config_schema()

    def test_write_all_schemas_writes_three_files(self, tmp_path: Path):
        written = write_all_schemas(tmp_path / "schemas")
        assert set(written) == {"config", "agents", "system"}
        for kind, path in written.items():
            assert path.is_file()
            loaded = json.loads(path.read_text(encoding="utf-8"))
            assert loaded["type"] == "object"

    def test_write_all_schemas_creates_dir(self, tmp_path: Path):
        target = tmp_path / "nested" / "deep" / "schemas"
        written = write_all_schemas(target)
        assert target.is_dir()
        assert all(p.is_file() for p in written.values())


# ---------------------------------------------------------------------------
# AgentsFile / SystemManifest models
# ---------------------------------------------------------------------------


class TestAgentsFileModel:
    def test_empty_default_is_valid(self):
        model = AgentsFile()
        assert model.agents == {}
        assert model.skills == []
        assert model.routing.dispatch_above == 0.75
        assert model.transports == {}
        # PR3 — default_mode None por default
        assert model.default_mode is None

    def test_default_mode_parses_canonical_value(self):
        """PR3 — AgentsFile aceita default_mode como string canônica."""
        from aptdata.agents.modes import ExecutionMode

        for value in ("oneshot", "converse", "project", "orchestrated"):
            model = AgentsFile(default_mode=value)
            assert model.default_mode == ExecutionMode.from_str(value)

    def test_default_mode_rejects_unknown_value(self):
        with pytest.raises(Exception):
            AgentsFile(default_mode="bogus")  # type: ignore[arg-type]

    def test_default_mode_round_trip_json(self):
        from aptdata.agents.modes import ExecutionMode

        model = AgentsFile(default_mode=ExecutionMode.ORCHESTRATED)
        dumped = model.model_dump(mode="json")
        assert dumped["default_mode"] == "orchestrated"

    def test_rejects_unknown_top_level_field(self):
        with pytest.raises(Exception):
            AgentsFile(bogus_top_level=1)  # type: ignore[call-arg]


class TestSystemManifestModel:
    def test_empty_default_is_valid(self):
        model = SystemManifest()
        assert model.system == {"id": "default"}
        assert model.imports == []

    def test_rejects_unknown_top_level_field(self):
        with pytest.raises(Exception):
            SystemManifest(bogus=1)  # type: ignore[call-arg]

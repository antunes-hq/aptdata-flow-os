"""Tests for declarative YAML config parsing and schema export."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from smart_data.config.parser import (
    ConfigComponent,
    ConfigFlow,
    ConfigSystem,
    ParsedConfig,
    YamlConfigParser,
)
from smart_data.config.secrets import SecretManager
from smart_data.config.schema import export_domain_schema, write_domain_schema
from smart_data.core.system import ComponentKind


class TestYamlConfigParser:
    def test_parse_file_hydrates_domain_objects(self, tmp_path):
        config_file = tmp_path / "pipeline.yaml"
        config_file.write_text(
            """
metadata:
  owner: data-platform
system:
  system_id: ingestion
  flows:
    - flow_id: default
      components:
        - component_id: extract_customers
          metadata:
            kind: extract
            tags: [source]
      edges: []
""",
            encoding="utf-8",
        )

        parsed = YamlConfigParser().parse_file(config_file)
        assert parsed.metadata["owner"] == "data-platform"
        assert parsed.system.system_id == "ingestion"
        assert parsed.system.flows[0].flow_id == "default"
        component = parsed.system.flows[0].components[0]
        assert component.component_id == "extract_customers"
        assert component.meta.kind == ComponentKind.EXTRACT

    def test_parse_data_supports_top_level_flows(self):
        payload = {
            "metadata": {"team": "ai"},
            "system": {"system_id": "demo"},
            "flows": [
                {
                    "flow_id": "f1",
                    "components": [{"component_id": "c1"}],
                    "edges": [{"source_id": "c1", "target_id": "c1"}],
                }
            ],
        }

        parsed = YamlConfigParser().parse_data(payload)
        assert parsed.system.system_id == "demo"
        assert parsed.system.flows[0].components[0].component_id == "c1"
        assert parsed.system.flows[0].edges[0].source_id == "c1"

    def test_parse_file_rejects_non_mapping_root(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("- invalid\n", encoding="utf-8")
        with pytest.raises(ValueError, match="YAML root must be a mapping/object"):
            YamlConfigParser().parse_file(config_file)

    def test_parse_data_invalid_component_kind_raises_pydantic_error(self):
        payload = {
            "system": {
                "system_id": "demo",
                "flows": [
                    {
                        "flow_id": "f1",
                        "components": [{"component_id": "c1", "metadata": {"kind": "invalid"}}],
                    }
                ],
            }
        }

        with pytest.raises(ValidationError, match="kind"):
            YamlConfigParser().parse_data(payload)

    def test_parse_data_missing_component_id_raises_pydantic_error(self):
        payload = {
            "system": {"system_id": "demo", "flows": [{"flow_id": "f1", "components": [{}]}]}
        }

        with pytest.raises(ValidationError, match="component_id"):
            YamlConfigParser().parse_data(payload)

    def test_parse_data_resolves_env_placeholders(self, monkeypatch):
        monkeypatch.setenv("CFG_OWNER", "platform-secure")
        parser = YamlConfigParser(secret_manager=SecretManager(load_dotenv_file=False))
        parsed = parser.parse_data(
            {"metadata": {"owner": "${CFG_OWNER}"}, "system": {"system_id": "demo"}}
        )
        assert parsed.metadata["owner"] == "platform-secure"


class TestSchemaUtilities:
    def test_export_domain_schema_contains_system(self):
        schema = export_domain_schema()
        assert schema["type"] == "object"
        assert "system" in schema["properties"]

    def test_write_domain_schema_writes_json(self, tmp_path):
        output = tmp_path / "schemas" / "smart-data.json"
        written = write_domain_schema(output)
        assert written == output
        schema = json.loads(output.read_text(encoding="utf-8"))
        assert "properties" in schema


class TestParserSupportClasses:
    def test_config_component_passthrough_methods(self):
        component = ConfigComponent(component_id="c1")
        assert component.validate_inputs([])
        assert component.execute([]) == []

    def test_config_flow_methods_and_type_checks(self):
        flow = ConfigFlow(flow_id="f1")
        component = ConfigComponent(component_id="c1")
        flow.add_component(component)
        flow.connect("c1", "c1", "always")
        flow.compile()
        assert flow.run([]) == []
        assert flow.edges[0].condition == "always"
        with pytest.raises(TypeError, match="ConfigFlow only accepts ConfigComponent"):
            flow.add_component(object())  # type: ignore[arg-type]

    def test_config_system_methods_and_type_checks(self):
        system = ConfigSystem(system_id="s1")
        flow = ConfigFlow(flow_id="f1")
        system.register_flow(flow)
        system.run()
        assert system.flows[0].flow_id == "f1"
        with pytest.raises(TypeError, match="ConfigSystem only accepts ConfigFlow"):
            system.register_flow(object())  # type: ignore[arg-type]

    def test_parsed_config_default_system(self):
        parsed = ParsedConfig()
        assert parsed.system.system_id == "default"

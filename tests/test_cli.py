"""Tests for the CLI (aptdata.cli.app)."""

from __future__ import annotations

import json

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic.dataclasses import dataclass as pydantic_dataclass
from typer.testing import CliRunner

from aptdata.cli.app import _emit, app
from aptdata.core.dataset import BaseDataset
from aptdata.core.system import BaseSystem
from aptdata.plugins import registry

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers – minimal system registered for CLI tests
# ---------------------------------------------------------------------------


@pydantic_dataclass
class _MockDataset(BaseDataset):
    def read(self):
        return []

    def write(self, data):
        pass


@pydantic_dataclass
class _MockSystem(BaseSystem):
    def __post_init__(self) -> None:
        self._flows = []

    def register_flow(self, flow):
        self._flows.append(flow)

    def run(self):
        pass  # no-op for tests


# Register at module level so tests share it
registry.register("mock_pipeline", _MockSystem)


# ---------------------------------------------------------------------------
# `aptdata run` tests
# ---------------------------------------------------------------------------


class TestRunCommand:
    def test_help(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "pipeline" in result.output.lower()

    def test_run_known_pipeline_exits_0(self):
        result = runner.invoke(app, ["run", "mock_pipeline"])
        assert result.exit_code == 0
        # stdout should contain two JSON events
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert len(lines) >= 2
        started = json.loads(lines[0])
        completed = json.loads(lines[-1])
        assert started["event"] == "pipeline.started"
        assert completed["event"] == "pipeline.completed"

    def test_run_with_env_option(self):
        result = runner.invoke(app, ["run", "mock_pipeline", "--env", "prod"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        started = json.loads(lines[0])
        assert started["env"] == "prod"

    def test_run_dry_run_flag(self):
        result = runner.invoke(app, ["run", "mock_pipeline", "--dry-run"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        started = json.loads(lines[0])
        assert started["dry_run"] is True

    def test_run_unknown_pipeline_exits_1(self):
        result = runner.invoke(app, ["run", "nonexistent_pipeline"])
        assert result.exit_code == 1

    def test_run_unknown_pipeline_emits_error_json(self):
        result = runner.invoke(app, ["run", "nonexistent_pipeline"])
        # stderr and stdout are merged by the test runner
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert len(lines) >= 1
        error_event = json.loads(lines[-1])
        assert error_event["event"] == "pipeline.error"
        assert "nonexistent_pipeline" in error_event["error"]


# ---------------------------------------------------------------------------
# Plugin registry tests
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def test_register_and_get(self):
        from aptdata.plugins import _SystemRegistry

        reg = _SystemRegistry()
        reg.register("s1", _MockSystem)
        assert reg.get("s1") is _MockSystem

    def test_get_missing_returns_none(self):
        from aptdata.plugins import _SystemRegistry

        reg = _SystemRegistry()
        assert reg.get("missing") is None

    def test_list_systems(self):
        from aptdata.plugins import _SystemRegistry

        reg = _SystemRegistry()
        reg.register("b", _MockSystem)
        reg.register("a", _MockSystem)
        assert reg.list_systems() == ["a", "b"]


class TestScaffoldCommand:
    def test_scaffold_creates_hello_world_project(self, tmp_path):
        project_name = "selecao_demo"
        result = runner.invoke(
            app, ["scaffold", project_name, "--output", str(tmp_path)]
        )

        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert len(lines) >= 2
        assert json.loads(lines[0])["event"] == "scaffold.started"
        completed_event = json.loads(lines[-1])
        assert completed_event["event"] == "scaffold.completed"

        project_dir = tmp_path / project_name
        assert (project_dir / "main.py").exists()
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / "data" / "selecao_brasileira.json").exists()
        assert (project_dir / "output").exists()

    def test_scaffold_rejects_invalid_project_name(self):
        result = runner.invoke(app, ["scaffold", "123-invalid"])
        assert result.exit_code == 1
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert json.loads(lines[-1])["event"] == "scaffold.error"

    def test_scaffold_fails_if_directory_exists(self, tmp_path):
        project_dir = tmp_path / "existing_project"
        project_dir.mkdir()

        result = runner.invoke(
            app, ["scaffold", "existing_project", "--output", str(tmp_path)]
        )
        assert result.exit_code == 1
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert json.loads(lines[-1])["event"] == "scaffold.error"


class TestSchemaCommand:
    def test_schema_export_writes_json_schema(self, tmp_path):
        output = tmp_path / "schema.json"
        result = runner.invoke(app, ["schema", "export", "--output", str(output)])

        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert json.loads(lines[0])["event"] == "schema.export.started"
        assert json.loads(lines[-1])["event"] == "schema.export.completed"
        assert output.exists()

        schema = json.loads(output.read_text(encoding="utf-8"))
        assert schema["type"] == "object"
        assert "system" in schema.get("properties", {})


class TestEmit:
    def test_emit_includes_trace_id(self, capsys):
        exporter = InMemorySpanExporter()
        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            provider.add_span_processor(SimpleSpanProcessor(exporter))
        else:
            provider = TracerProvider()
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            trace.set_tracer_provider(provider)

        tracer = trace.get_tracer("tests.cli")
        with tracer.start_as_current_span("cli_test"):
            _emit({"event": "custom"})
        payload = json.loads(capsys.readouterr().out.strip())
        assert payload["event"] == "custom"
        assert payload["trace_id"] is not None

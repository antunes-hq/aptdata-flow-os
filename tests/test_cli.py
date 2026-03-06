"""Tests for the CLI (smart_data.cli.app)."""

from __future__ import annotations

import json

import pytest
from pydantic.dataclasses import dataclass as pydantic_dataclass
from typer.testing import CliRunner

from smart_data.cli.app import app
from smart_data.plugins import registry
from smart_data.core.pipeline import BasePipeline, IPipeline
from smart_data.core.step import BaseStep, IStep
from smart_data.core.dataset import BaseDataset, IDataset


runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers – minimal pipeline registered for CLI tests
# ---------------------------------------------------------------------------


@pydantic_dataclass
class _MockDataset(BaseDataset):
    def read(self):
        return []

    def write(self, data):
        pass


@pydantic_dataclass
class _MockStep(BaseStep):
    def validate_inputs(self, inputs):
        return True

    def execute(self, inputs):
        return _MockDataset(uri="memory://out")


@pydantic_dataclass
class _MockPipeline(BasePipeline):
    def __post_init__(self) -> None:
        self._compiled = False

    def register_step(self, step):
        pass

    def compile_dag(self):
        self._compiled = True

    def run(self):
        pass  # no-op for tests


# Register at module level so tests share it
registry.register("mock_pipeline", _MockPipeline)


# ---------------------------------------------------------------------------
# `smart-data run` tests
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
        lines = [l for l in result.output.strip().splitlines() if l.strip()]
        assert len(lines) >= 2
        started = json.loads(lines[0])
        completed = json.loads(lines[-1])
        assert started["event"] == "pipeline.started"
        assert completed["event"] == "pipeline.completed"

    def test_run_with_env_option(self):
        result = runner.invoke(app, ["run", "mock_pipeline", "--env", "prod"])
        assert result.exit_code == 0
        lines = [l for l in result.output.strip().splitlines() if l.strip()]
        started = json.loads(lines[0])
        assert started["env"] == "prod"

    def test_run_dry_run_flag(self):
        result = runner.invoke(app, ["run", "mock_pipeline", "--dry-run"])
        assert result.exit_code == 0
        lines = [l for l in result.output.strip().splitlines() if l.strip()]
        started = json.loads(lines[0])
        assert started["dry_run"] is True

    def test_run_unknown_pipeline_exits_1(self):
        result = runner.invoke(app, ["run", "nonexistent_pipeline"])
        assert result.exit_code == 1

    def test_run_unknown_pipeline_emits_error_json(self):
        result = runner.invoke(app, ["run", "nonexistent_pipeline"])
        # stderr and stdout are merged by the test runner
        lines = [l for l in result.output.strip().splitlines() if l.strip()]
        assert len(lines) >= 1
        error_event = json.loads(lines[-1])
        assert error_event["event"] == "pipeline.error"
        assert "nonexistent_pipeline" in error_event["error"]


# ---------------------------------------------------------------------------
# Plugin registry tests
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def test_register_and_get(self):
        from smart_data.plugins import _PipelineRegistry

        reg = _PipelineRegistry()
        reg.register("p1", _MockPipeline)
        assert reg.get("p1") is _MockPipeline

    def test_get_missing_returns_none(self):
        from smart_data.plugins import _PipelineRegistry

        reg = _PipelineRegistry()
        assert reg.get("missing") is None

    def test_list_pipelines(self):
        from smart_data.plugins import _PipelineRegistry

        reg = _PipelineRegistry()
        reg.register("b", _MockPipeline)
        reg.register("a", _MockPipeline)
        assert reg.list_pipelines() == ["a", "b"]

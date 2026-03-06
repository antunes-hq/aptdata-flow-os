"""Tests for the core abstract contracts."""

from __future__ import annotations

from typing import Any

from pydantic import Field
import pytest

from smart_data.core.dataset import AbstractDataset
from smart_data.core.pipeline import AbstractPipeline
from smart_data.core.step import AbstractStep


# ---------------------------------------------------------------------------
# Minimal concrete implementations used only within tests
# ---------------------------------------------------------------------------


class _SimpleDataset(AbstractDataset):
    """Concrete dataset that stores data in memory."""

    _data: Any = None

    def read(self) -> Any:
        return self._data

    def write(self, data: Any) -> None:
        self._data = data


class _DoubleStep(AbstractStep):
    """Concrete step that doubles every element of a list dataset."""

    def validate_inputs(self, inputs: list[AbstractDataset]) -> bool:
        return len(inputs) == 1

    def execute(self, inputs: list[AbstractDataset]) -> AbstractDataset:
        source = inputs[0]
        data = source.read()
        out = _SimpleDataset(uri="memory://output", schema_metadata={"type": "list"})
        out.write([x * 2 for x in data])
        return out


class _SimplePipeline(AbstractPipeline):
    """Concrete pipeline with a flat list of steps."""

    steps: list[AbstractStep] = Field(default_factory=list)
    _compiled: bool = False

    def register_step(self, step: AbstractStep) -> None:
        self.steps.append(step)

    def compile_dag(self) -> None:
        self._compiled = True

    def run(self) -> None:
        if not self._compiled:
            raise RuntimeError("Pipeline not compiled.")
        ds = _SimpleDataset(uri="memory://input")
        ds.write([1, 2, 3])
        inputs: list[AbstractDataset] = [ds]
        for step in self.steps:
            if step.validate_inputs(inputs):
                result = step.execute(inputs)
                inputs = [result]


# ---------------------------------------------------------------------------
# AbstractDataset tests
# ---------------------------------------------------------------------------


class TestAbstractDataset:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            AbstractDataset(uri="s3://bucket/file")  # type: ignore[abstract]

    def test_concrete_instantiation(self):
        ds = _SimpleDataset(uri="memory://test")
        assert ds.uri == "memory://test"
        assert ds.schema_metadata == {}

    def test_schema_metadata_field(self):
        ds = _SimpleDataset(uri="s3://bucket/file", schema_metadata={"format": "parquet"})
        assert ds.schema_metadata["format"] == "parquet"

    def test_read_write_roundtrip(self):
        ds = _SimpleDataset(uri="memory://data")
        ds.write({"key": "value"})
        assert ds.read() == {"key": "value"}

    def test_uri_is_required(self):
        with pytest.raises(Exception):
            _SimpleDataset()  # missing required field


# ---------------------------------------------------------------------------
# AbstractStep tests
# ---------------------------------------------------------------------------


class TestAbstractStep:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            AbstractStep(step_id="s1")  # type: ignore[abstract]

    def test_step_id_field(self):
        step = _DoubleStep(step_id="double_step")
        assert step.step_id == "double_step"

    def test_validate_inputs_valid(self):
        ds = _SimpleDataset(uri="memory://in")
        step = _DoubleStep(step_id="s1")
        assert step.validate_inputs([ds]) is True

    def test_validate_inputs_invalid(self):
        step = _DoubleStep(step_id="s1")
        assert step.validate_inputs([]) is False

    def test_execute_doubles_values(self):
        ds = _SimpleDataset(uri="memory://in")
        ds.write([1, 2, 3])
        step = _DoubleStep(step_id="s1")
        result = step.execute([ds])
        assert result.read() == [2, 4, 6]


# ---------------------------------------------------------------------------
# AbstractPipeline tests
# ---------------------------------------------------------------------------


class TestAbstractPipeline:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            AbstractPipeline()  # type: ignore[abstract]

    def test_register_and_run(self):
        pipeline = _SimplePipeline()
        step = _DoubleStep(step_id="double")
        pipeline.register_step(step)
        assert len(pipeline.steps) == 1

    def test_compile_then_run(self):
        pipeline = _SimplePipeline()
        pipeline.register_step(_DoubleStep(step_id="d1"))
        pipeline.compile_dag()
        assert pipeline._compiled is True
        pipeline.run()  # should not raise

    def test_run_without_compile_raises(self):
        pipeline = _SimplePipeline()
        pipeline.register_step(_DoubleStep(step_id="d1"))
        with pytest.raises(RuntimeError, match="not compiled"):
            pipeline.run()

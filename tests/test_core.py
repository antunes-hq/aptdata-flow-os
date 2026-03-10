"""Tests for the core dataset interface and base class."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic.dataclasses import dataclass as pydantic_dataclass

from aptdata.core.dataset import BaseDataset, IDataset

# ---------------------------------------------------------------------------
# Minimal concrete implementation used only within tests
# ---------------------------------------------------------------------------


@pydantic_dataclass
class _SimpleDataset(BaseDataset):
    """Concrete dataset that stores data in memory."""

    def __post_init__(self) -> None:
        self._data: Any = None

    def read(self) -> Any:
        return self._data

    def write(self, data: Any) -> None:
        self._data = data


# ---------------------------------------------------------------------------
# IDataset / BaseDataset tests
# ---------------------------------------------------------------------------


class TestIDataset:
    def test_cannot_instantiate_interface(self):
        with pytest.raises(TypeError):
            IDataset()  # type: ignore[abstract]

    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            BaseDataset(uri="s3://bucket/file")  # type: ignore[abstract]

    def test_concrete_instantiation(self):
        ds = _SimpleDataset(uri="memory://test")
        assert ds.uri == "memory://test"
        assert ds.schema_metadata == {}

    def test_schema_metadata_field(self):
        ds = _SimpleDataset(
            uri="s3://bucket/file", schema_metadata={"format": "parquet"}
        )
        assert ds.schema_metadata["format"] == "parquet"

    def test_read_write_roundtrip(self):
        ds = _SimpleDataset(uri="memory://data")
        ds.write({"key": "value"})
        assert ds.read() == {"key": "value"}

    def test_uri_is_required(self):
        with pytest.raises(Exception):
            _SimpleDataset()  # missing required field

    def test_concrete_is_instance_of_interface(self):
        ds = _SimpleDataset(uri="memory://test")
        assert isinstance(ds, IDataset)
        assert isinstance(ds, BaseDataset)

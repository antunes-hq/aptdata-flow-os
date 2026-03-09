"""Tests for transform plugins — PandasTransformer, PySparkTransformer, BaseTransformer."""

from __future__ import annotations

import pytest

from smart_data.plugins.base import BaseTransformer
from smart_data.plugins.manager import PluginDependencyError


# ---------------------------------------------------------------------------
# BaseTransformer ABC
# ---------------------------------------------------------------------------


class TestBaseTransformer:
    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            BaseTransformer()  # type: ignore[abstract]

    def test_concrete_requires_name_and_transform(self) -> None:
        class _Concrete(BaseTransformer):
            @property
            def name(self) -> str:
                return "test"

            def transform(self, data):
                return data

        t = _Concrete()
        assert t.name == "test"
        assert t.transform([1, 2, 3]) == [1, 2, 3]

    def test_missing_transform_raises(self) -> None:
        class _MissingTransform(BaseTransformer):
            @property
            def name(self) -> str:
                return "x"

        with pytest.raises(TypeError):
            _MissingTransform()  # type: ignore[abstract]

    def test_missing_name_raises(self) -> None:
        class _MissingName(BaseTransformer):
            def transform(self, data):
                return data

        with pytest.raises(TypeError):
            _MissingName()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# PandasTransformer
# ---------------------------------------------------------------------------

pandas = pytest.importorskip("pandas", reason="pandas not installed")


class TestPandasTransformer:
    def test_name_property(self) -> None:
        from smart_data.plugins.transform import PandasTransformer

        t = PandasTransformer("my_transformer", lambda df: df)
        assert t.name == "my_transformer"

    def test_transform_dataframe(self) -> None:
        import pandas as pd

        from smart_data.plugins.transform import PandasTransformer

        def double(df: pd.DataFrame) -> pd.DataFrame:
            return df.assign(value=df["value"] * 2)

        t = PandasTransformer("double", double)
        df = pd.DataFrame({"value": [1, 2, 3]})
        result = t.transform(df)
        assert list(result["value"]) == [2, 4, 6]

    def test_transform_list_of_dicts(self) -> None:
        import pandas as pd

        from smart_data.plugins.transform import PandasTransformer

        def add_flag(df: pd.DataFrame) -> pd.DataFrame:
            return df.assign(flag=True)

        t = PandasTransformer("add_flag", add_flag)
        result = t.transform([{"id": 1}, {"id": 2}])
        assert isinstance(result, pd.DataFrame)
        assert "flag" in result.columns
        assert len(result) == 2

    def test_transform_in_memory_dataset_returns_dataset(self) -> None:

        from smart_data.plugins.dataset import InMemoryDataset
        from smart_data.plugins.transform import PandasTransformer

        def noop(df):
            return df

        t = PandasTransformer("noop", noop)
        ds = InMemoryDataset(uri="memory://test", schema_metadata={})
        ds.write([{"id": 1, "val": 10}, {"id": 2, "val": 20}])
        result = t.transform(ds)
        assert isinstance(result, InMemoryDataset)
        assert len(result) == 2

    def test_transform_preserves_uri(self) -> None:

        from smart_data.plugins.dataset import InMemoryDataset
        from smart_data.plugins.transform import PandasTransformer

        t = PandasTransformer("noop", lambda df: df)
        ds = InMemoryDataset(uri="memory://my_uri", schema_metadata={})
        ds.write([{"id": 1}])
        result = t.transform(ds)
        assert isinstance(result, InMemoryDataset)
        assert result.uri == "memory://my_uri"

    def test_rows_reduced(self) -> None:
        import pandas as pd

        from smart_data.plugins.transform import PandasTransformer

        def filter_row(df: pd.DataFrame) -> pd.DataFrame:
            return df[df["value"] > 1]

        t = PandasTransformer("filter", filter_row)
        df = pd.DataFrame({"value": [1, 2, 3]})
        result = t.transform(df)
        assert len(result) == 2

    def test_is_base_transformer(self) -> None:
        from smart_data.plugins.transform import PandasTransformer

        t = PandasTransformer("x", lambda df: df)
        assert isinstance(t, BaseTransformer)

    def test_transform_empty_data(self) -> None:
        import pandas as pd

        from smart_data.plugins.transform import PandasTransformer

        t = PandasTransformer("noop", lambda df: df)
        result = t.transform([])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# PySparkTransformer (interface only — skip if pyspark not installed)
# ---------------------------------------------------------------------------


class TestPySparkTransformerInterface:
    def test_import_class(self) -> None:
        """PySparkTransformer class can always be imported without pyspark installed."""
        from smart_data.plugins.transform import PySparkTransformer  # noqa: F401

    def test_is_base_transformer_subclass(self) -> None:
        from smart_data.plugins.transform import PySparkTransformer

        assert issubclass(PySparkTransformer, BaseTransformer)

    def test_dependency_error_when_pyspark_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Instantiation raises PluginDependencyError when pyspark is not available."""
        import builtins

        real_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "pyspark":
                raise ImportError("No module named 'pyspark'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _mock_import)

        # Import the class (this does NOT check for pyspark at import time).
        from smart_data.plugins.transform.spark import PySparkTransformer

        # Instantiation triggers the lazy import check.
        with pytest.raises((PluginDependencyError, ImportError)):
            PySparkTransformer("t", lambda s, df: df)

"""Local filesystem plugin — CSV, JSON, and Parquet readers / writers.

All classes produce or consume :class:`~smart_data.plugins.dataset.InMemoryDataset`
instances backed by lists of dictionaries (records).

CSV and JSON support is built-in (stdlib ``csv`` / ``json``).
Parquet support requires the optional ``pyarrow`` package; a friendly
:class:`~smart_data.plugins.manager.PluginDependencyError` is raised if
it is not installed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from smart_data.core.dataset import BaseDataset
from smart_data.plugins.base import BaseReader, BaseWriter
from smart_data.plugins.dataset import InMemoryDataset
from smart_data.plugins.manager import PluginDependencyError

# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


class CSVReader(BaseReader):
    """Read a CSV file into an :class:`InMemoryDataset`.

    Parameters
    ----------
    filepath:
        Path to the CSV file on the local filesystem.
    encoding:
        File encoding (default ``"utf-8"``).
    delimiter:
        Column delimiter (default ``","``).
    """

    def __init__(
        self,
        filepath: str,
        *,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ) -> None:
        self.filepath = Path(filepath)
        self.encoding = encoding
        self.delimiter = delimiter

    def read(self, **kwargs: Any) -> InMemoryDataset:
        with open(self.filepath, newline="", encoding=self.encoding) as fh:
            reader = csv.DictReader(fh, delimiter=self.delimiter)
            records = list(reader)
        ds = InMemoryDataset(uri=str(self.filepath))
        ds.write(records)
        return ds


class CSVWriter(BaseWriter):
    """Write an :class:`InMemoryDataset` to a CSV file.

    Parameters
    ----------
    filepath:
        Destination path on the local filesystem.
    encoding:
        File encoding (default ``"utf-8"``).
    delimiter:
        Column delimiter (default ``","``).
    """

    def __init__(
        self,
        filepath: str,
        *,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ) -> None:
        self.filepath = Path(filepath)
        self.encoding = encoding
        self.delimiter = delimiter

    def write(self, dataset: BaseDataset, **kwargs: Any) -> None:
        records: list[dict[str, Any]] = dataset.read()
        if not records:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text("", encoding=self.encoding)
            return

        fieldnames = list(records[0].keys())
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", newline="", encoding=self.encoding) as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=self.delimiter)
            writer.writeheader()
            writer.writerows(records)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


class JSONReader(BaseReader):
    """Read a JSON file (array of objects) into an :class:`InMemoryDataset`.

    Parameters
    ----------
    filepath:
        Path to the JSON file.
    encoding:
        File encoding (default ``"utf-8"``).
    """

    def __init__(self, filepath: str, *, encoding: str = "utf-8") -> None:
        self.filepath = Path(filepath)
        self.encoding = encoding

    def read(self, **kwargs: Any) -> InMemoryDataset:
        with open(self.filepath, encoding=self.encoding) as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("JSON file must contain an array of objects.")
        ds = InMemoryDataset(uri=str(self.filepath))
        ds.write(data)
        return ds


class JSONWriter(BaseWriter):
    """Write an :class:`InMemoryDataset` to a JSON file (array of objects).

    Parameters
    ----------
    filepath:
        Destination path.
    encoding:
        File encoding (default ``"utf-8"``).
    indent:
        JSON indentation level (default ``2``).
    """

    def __init__(
        self,
        filepath: str,
        *,
        encoding: str = "utf-8",
        indent: int = 2,
    ) -> None:
        self.filepath = Path(filepath)
        self.encoding = encoding
        self.indent = indent

    def write(self, dataset: BaseDataset, **kwargs: Any) -> None:
        records: list[dict[str, Any]] = dataset.read()
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding=self.encoding) as fh:
            json.dump(records, fh, indent=self.indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Parquet (optional dependency: pyarrow)
# ---------------------------------------------------------------------------


class ParquetReader(BaseReader):
    """Read a Parquet file into an :class:`InMemoryDataset`.

    Requires the ``pyarrow`` package.

    Parameters
    ----------
    filepath:
        Path to the ``.parquet`` file.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath)

    def read(self, **kwargs: Any) -> InMemoryDataset:
        try:
            import pyarrow.parquet as pq  # noqa: WPS433
        except ImportError:
            raise PluginDependencyError("ParquetReader", "pyarrow") from None

        table = pq.read_table(str(self.filepath))
        records: list[dict[str, Any]] = table.to_pydict()
        # Convert columnar dict to list-of-dicts
        keys = list(records.keys())
        row_count = len(records[keys[0]]) if keys else 0
        rows = [{k: records[k][i] for k in keys} for i in range(row_count)]

        ds = InMemoryDataset(uri=str(self.filepath))
        ds.write(rows)
        return ds


class ParquetWriter(BaseWriter):
    """Write an :class:`InMemoryDataset` to a Parquet file.

    Requires the ``pyarrow`` package.

    Parameters
    ----------
    filepath:
        Destination ``.parquet`` path.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath)

    def write(self, dataset: BaseDataset, **kwargs: Any) -> None:
        try:
            import pyarrow as pa  # noqa: WPS433
            import pyarrow.parquet as pq  # noqa: WPS433
        except ImportError:
            raise PluginDependencyError("ParquetWriter", "pyarrow") from None

        records: list[dict[str, Any]] = dataset.read()
        if not records:
            # Write an empty parquet with no columns
            table = pa.table({})
        else:
            # Convert list-of-dicts to columnar dict
            keys = list(records[0].keys())
            columnar = {k: [r[k] for r in records] for k in keys}
            table = pa.table(columnar)

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, str(self.filepath))


__all__ = [
    "CSVReader",
    "CSVWriter",
    "JSONReader",
    "JSONWriter",
    "ParquetReader",
    "ParquetWriter",
]

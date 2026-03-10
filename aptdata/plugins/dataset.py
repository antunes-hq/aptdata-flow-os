"""In-memory dataset for plugin data exchange.

Provides :class:`InMemoryDataset`, a concrete :class:`BaseDataset`
subclass that holds tabular data as a list of dictionaries (records).
Plugin readers produce ``InMemoryDataset`` instances and writers
consume them.
"""

from __future__ import annotations

from typing import Any

from pydantic.dataclasses import dataclass as pydantic_dataclass

from aptdata.core.dataset import BaseDataset


@pydantic_dataclass
class InMemoryDataset(BaseDataset):
    """Concrete dataset that stores records in memory.

    Parameters
    ----------
    uri:
        Logical URI describing the data origin (informational).
    schema_metadata:
        Optional schema metadata mapping.
    """

    def __post_init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    # -- IDataset interface -------------------------------------------------

    def read(self) -> list[dict[str, Any]]:
        """Return the in-memory records."""
        return list(self._records)

    def write(self, data: Any) -> None:
        """Replace the in-memory records with *data*.

        Parameters
        ----------
        data:
            A list of dictionaries (records).
        """
        if not isinstance(data, list):
            raise TypeError("InMemoryDataset expects a list of dicts.")
        self._records = data

    # -- convenience --------------------------------------------------------

    @property
    def records(self) -> list[dict[str, Any]]:
        """Return the stored records (read-only view)."""
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)


__all__ = ["InMemoryDataset"]

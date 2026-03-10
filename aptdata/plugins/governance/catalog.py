"""Dataset catalog for governance and discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aptdata.plugins.quality.contract import ColumnClassification, SchemaContract


@dataclass
class DatasetCatalogEntry:
    """Catalog record for a single dataset.

    Parameters
    ----------
    uri:
        Unique logical URI for the dataset (used as the catalog key).
    name:
        Human-readable dataset name.
    description:
        Description of the dataset contents.
    owner:
        Team or person responsible for this dataset.
    schema_contract:
        Optional :class:`~aptdata.plugins.quality.contract.SchemaContract`
        governing this dataset.
    tags:
        Free-form classification tags.
    classification:
        Overall data sensitivity classification.
    created_at:
        UTC ISO-8601 timestamp when the entry was first registered.
    updated_at:
        UTC ISO-8601 timestamp of the most recent update.
    metadata:
        Arbitrary extra metadata.
    """

    uri: str
    name: str = ""
    description: str = ""
    owner: str = ""
    schema_contract: SchemaContract | None = None
    tags: list[str] = field(default_factory=list)
    classification: ColumnClassification = ColumnClassification.INTERNAL
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)


class DatasetCatalog:
    """In-memory catalog of :class:`DatasetCatalogEntry` objects.

    Examples
    --------
    ::

        catalog = DatasetCatalog()
        catalog.register(DatasetCatalogEntry(uri="s3://bucket/data.parquet", name="Sales"))
        entry = catalog.get("s3://bucket/data.parquet")
        results = catalog.search(owner="data-team", tag="finance")
    """

    def __init__(self) -> None:
        self._entries: dict[str, DatasetCatalogEntry] = {}

    def register(self, entry: DatasetCatalogEntry) -> None:
        """Register or replace a catalog entry under its :attr:`~DatasetCatalogEntry.uri`."""
        self._entries[entry.uri] = entry

    def get(self, uri: str) -> DatasetCatalogEntry | None:
        """Return the entry for *uri*, or ``None`` if not found."""
        return self._entries.get(uri)

    def search(
        self,
        owner: str | None = None,
        tag: str | None = None,
        classification: ColumnClassification | None = None,
    ) -> list[DatasetCatalogEntry]:
        """Search catalog entries with optional filters.

        Parameters
        ----------
        owner:
            If provided, only entries owned by this owner are returned.
        tag:
            If provided, only entries with this tag are returned.
        classification:
            If provided, only entries with this classification are returned.
        """
        results = list(self._entries.values())
        if owner is not None:
            results = [e for e in results if e.owner == owner]
        if tag is not None:
            results = [e for e in results if tag in e.tags]
        if classification is not None:
            results = [e for e in results if e.classification == classification]
        return results

    def list_entries(self) -> list[DatasetCatalogEntry]:
        """Return all registered catalog entries."""
        return list(self._entries.values())


__all__ = ["DatasetCatalogEntry", "DatasetCatalog"]

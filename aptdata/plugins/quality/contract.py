"""Schema contracts and column classification definitions.

Provides :class:`SchemaContract` for declaring the expected schema of a
dataset, including column types, nullability, classification, and PII
annotations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ColumnClassification(str, Enum):
    """Data sensitivity classification for a column or dataset."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    PII = "PII"
    PHI = "PHI"
    FINANCIAL = "FINANCIAL"
    SENSITIVE = "SENSITIVE"


class EnforcementMode(str, Enum):
    """How the quality framework reacts when a contract is violated.

    ABORT
        Raise an exception immediately.
    WARN
        Log a warning but continue processing.
    TAG
        Annotate the data with quality metadata and continue.
    """

    ABORT = "ABORT"
    WARN = "WARN"
    TAG = "TAG"


@dataclass
class ColumnContract:
    """Contract specification for a single column.

    Parameters
    ----------
    name:
        Column name as it appears in the dataset.
    dtype:
        Expected data type (e.g. ``"int64"``, ``"str"``).
    nullable:
        Whether ``null`` / ``None`` values are allowed.
    classification:
        Sensitivity classification (see :class:`ColumnClassification`).
    description:
        Human-readable description.
    pii:
        Shorthand flag indicating the column contains personally
        identifiable information.
    retention_days:
        Number of days the column's data must be retained.
    metadata:
        Arbitrary extra metadata.
    """

    name: str
    dtype: str = ""
    nullable: bool = True
    classification: ColumnClassification = ColumnClassification.INTERNAL
    description: str = ""
    pii: bool = False
    retention_days: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaContract:
    """Contract specification for an entire dataset schema.

    Parameters
    ----------
    name:
        Contract identifier.
    version:
        Semantic version string (e.g. ``"1.0.0"``).
    owner:
        Team or person responsible for this contract.
    description:
        Human-readable description.
    columns:
        Ordered list of :class:`ColumnContract` definitions.
    enforcement:
        How violations are handled (see :class:`EnforcementMode`).
    metadata:
        Arbitrary extra metadata.
    """

    name: str
    version: str = "1.0.0"
    owner: str = ""
    description: str = ""
    columns: list[ColumnContract] = field(default_factory=list)
    enforcement: EnforcementMode = EnforcementMode.ABORT
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_pii_columns(self) -> list[ColumnContract]:
        """Return columns that are flagged as PII."""
        return [
            c
            for c in self.columns
            if c.pii or c.classification == ColumnClassification.PII
        ]

    def get_columns_by_classification(
        self, classification: ColumnClassification
    ) -> list[ColumnContract]:
        """Return columns whose classification matches *classification*."""
        return [c for c in self.columns if c.classification == classification]


__all__ = [
    "ColumnClassification",
    "EnforcementMode",
    "ColumnContract",
    "SchemaContract",
]

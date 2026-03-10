"""Governance plugin package.

Provides business rules registry, dataset catalog, data classification
policies, and lineage store.
"""

from __future__ import annotations

from aptdata.plugins.governance.catalog import DatasetCatalog, DatasetCatalogEntry
from aptdata.plugins.governance.classification import (
    ColumnClassification,
    DataClassificationPolicy,
)
from aptdata.plugins.governance.lineage_store import LineageStore
from aptdata.plugins.governance.rules import (
    BusinessRule,
    RuleAuditEntry,
    RuleRegistry,
    RuleStatus,
)

__all__ = [
    "DatasetCatalog",
    "DatasetCatalogEntry",
    "ColumnClassification",
    "DataClassificationPolicy",
    "LineageStore",
    "BusinessRule",
    "RuleAuditEntry",
    "RuleRegistry",
    "RuleStatus",
]

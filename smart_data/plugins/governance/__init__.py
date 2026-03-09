"""Governance plugin package.

Provides business rules registry, dataset catalog, data classification
policies, and lineage store.
"""

from __future__ import annotations

from smart_data.plugins.governance.catalog import DatasetCatalog, DatasetCatalogEntry
from smart_data.plugins.governance.classification import (
    ColumnClassification,
    DataClassificationPolicy,
)
from smart_data.plugins.governance.lineage_store import LineageStore
from smart_data.plugins.governance.rules import (
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

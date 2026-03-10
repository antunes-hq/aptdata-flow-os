"""Data quality plugin package.

Re-exports the main public API for data contracts, quality expectations,
validation, and reporting.
"""

from __future__ import annotations

from aptdata.plugins.quality.contract import (
    ColumnClassification,
    ColumnContract,
    EnforcementMode,
    SchemaContract,
)
from aptdata.plugins.quality.expectations import (
    BaseExpectation,
    ExpectColumnToNotBeNull,
    ExpectColumnValuesInRange,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToMatchRegex,
)
from aptdata.plugins.quality.report import CheckResult, CheckStatus, QualityReport
from aptdata.plugins.quality.validator import QualityValidator

__all__ = [
    "ColumnClassification",
    "ColumnContract",
    "EnforcementMode",
    "SchemaContract",
    "BaseExpectation",
    "ExpectColumnToNotBeNull",
    "ExpectColumnValuesInRange",
    "ExpectColumnValuesToBeUnique",
    "ExpectColumnValuesToMatchRegex",
    "CheckResult",
    "CheckStatus",
    "QualityReport",
    "QualityValidator",
]

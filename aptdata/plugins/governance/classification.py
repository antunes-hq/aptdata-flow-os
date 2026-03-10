"""Data classification convenience re-exports and policy definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Re-export for convenience so callers can do:
#   from aptdata.plugins.governance.classification import ColumnClassification
from aptdata.plugins.quality.contract import ColumnClassification


@dataclass
class DataClassificationPolicy:
    """Policy defining how data with a specific classification should be handled.

    Parameters
    ----------
    name:
        Policy name.
    description:
        Human-readable description of the policy.
    pii_columns:
        Column names that contain personally identifiable information.
    retention_days:
        Required data retention period in days.
    encryption_required:
        Whether data at rest must be encrypted.
    access_roles:
        Roles permitted to access data governed by this policy.
    metadata:
        Arbitrary extra metadata.
    """

    name: str
    description: str = ""
    pii_columns: list[str] = field(default_factory=list)
    retention_days: int = 0
    encryption_required: bool = False
    access_roles: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["ColumnClassification", "DataClassificationPolicy"]

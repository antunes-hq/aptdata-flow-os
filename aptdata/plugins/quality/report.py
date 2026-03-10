"""Quality check result and report types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CheckStatus(str, Enum):
    """Status of a single quality check."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"


@dataclass
class CheckResult:
    """Result of a single data quality expectation.

    Parameters
    ----------
    expectation_name:
        Class name or human-readable label of the expectation.
    column:
        Column name the check was applied to (empty for table-level checks).
    status:
        Whether the check passed, failed, or issued a warning.
    message:
        Human-readable description of the outcome.
    rows_evaluated:
        Total number of rows considered by the check.
    rows_failed:
        Number of rows that violated the expectation.
    metadata:
        Arbitrary extra metadata from the expectation.
    """

    expectation_name: str
    column: str = ""
    status: CheckStatus = CheckStatus.PASSED
    message: str = ""
    rows_evaluated: int = 0
    rows_failed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    """Aggregated quality report for a single dataset validation run.

    Parameters
    ----------
    dataset_uri:
        URI of the dataset that was validated.
    workflow_name:
        Name of the workflow that triggered validation.
    trace_id:
        OpenTelemetry trace identifier.
    timestamp:
        UTC ISO-8601 timestamp of when the report was generated.
    checks:
        Individual :class:`CheckResult` objects.
    """

    dataset_uri: str
    workflow_name: str = ""
    trace_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return ``True`` when no check has a FAILED status."""
        return all(c.status != CheckStatus.FAILED for c in self.checks)

    @property
    def summary(self) -> dict[str, int]:
        """Return counts of PASSED, FAILED, and WARNING results."""
        counts: dict[str, int] = {
            CheckStatus.PASSED: 0,
            CheckStatus.FAILED: 0,
            CheckStatus.WARNING: 0,
        }
        for check in self.checks:
            counts[check.status] += 1
        return counts


__all__ = ["CheckStatus", "CheckResult", "QualityReport"]

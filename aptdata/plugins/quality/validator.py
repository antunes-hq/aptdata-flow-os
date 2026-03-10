"""Quality validator — wraps expectations into a workflow-compatible step."""

from __future__ import annotations

import logging
import warnings
from typing import Any

from aptdata.plugins.quality.contract import EnforcementMode
from aptdata.plugins.quality.expectations import BaseExpectation
from aptdata.plugins.quality.report import CheckStatus, QualityReport
from aptdata.telemetry.instrumentation import get_tracer

logger = logging.getLogger(__name__)


class QualityValidator:
    """Runs a suite of :class:`~.expectations.BaseExpectation` objects against data.

    Parameters
    ----------
    expectations:
        List of expectations to evaluate.
    enforcement:
        How to react when an expectation fails
        (see :class:`~.contract.EnforcementMode`).
    name:
        Human-readable identifier used in OTel span names.

    Examples
    --------
    ::

        from aptdata.plugins.quality import (
            QualityValidator, ExpectColumnToNotBeNull, EnforcementMode
        )

        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("age")],
            enforcement=EnforcementMode.ABORT,
        )
        clean_df = validator.validate(df)
    """

    def __init__(
        self,
        expectations: list[BaseExpectation],
        enforcement: EnforcementMode = EnforcementMode.ABORT,
        name: str = "QualityValidator",
    ) -> None:
        self.expectations = expectations
        self.enforcement = enforcement
        self.name = name

    def validate(self, data: Any) -> Any:
        """Validate *data* against all expectations and return *data*.

        This method is compatible with :meth:`~aptdata.core.workflow.Workflow.add_step`.
        On success the original *data* object is returned unchanged.

        Parameters
        ----------
        data:
            A ``pd.DataFrame``, PySpark ``DataFrame``,
            :class:`~aptdata.plugins.dataset.InMemoryDataset`, or
            ``list[dict]``.

        Returns
        -------
        Any
            The original *data* object (pass-through).

        Raises
        ------
        ValueError
            When ``enforcement == ABORT`` and at least one expectation fails.
        """
        import pandas as pd  # type: ignore[import]

        from aptdata.plugins.dataset import InMemoryDataset

        # Resolve to a DataFrame for expectations.
        resolved: Any
        if isinstance(data, InMemoryDataset):
            resolved = pd.DataFrame(data.read())
        elif isinstance(data, list):
            resolved = pd.DataFrame(data)
        else:
            resolved = data

        dataset_uri = data.uri if isinstance(data, InMemoryDataset) else "unknown"
        report = QualityReport(dataset_uri=dataset_uri)

        tracer = get_tracer("aptdata.quality")
        with tracer.start_as_current_span(self.name) as span:
            span.set_attribute("aptdata.quality.validator_name", self.name)
            span.set_attribute("aptdata.quality.enforcement", self.enforcement.value)
            span.set_attribute(
                "aptdata.quality.num_expectations", len(self.expectations)
            )

            for expectation in self.expectations:
                result = expectation.validate(resolved)
                report.checks.append(result)

            passed = report.passed
            span.set_attribute("aptdata.quality.passed", passed)
            span.set_attribute("aptdata.quality.num_checks", len(report.checks))
            failed_count = report.summary.get(CheckStatus.FAILED, 0)
            span.set_attribute("aptdata.quality.failed_checks", failed_count)

        if not passed:
            failed_checks = [c for c in report.checks if c.status == CheckStatus.FAILED]
            summary_msg = "; ".join(c.message for c in failed_checks)

            if self.enforcement == EnforcementMode.ABORT:
                raise ValueError(
                    f"Data quality validation failed [{self.name}]: {summary_msg}"
                )
            elif self.enforcement == EnforcementMode.WARN:
                warnings.warn(
                    f"Data quality warning [{self.name}]: {summary_msg}",
                    stacklevel=2,
                )
                logger.warning("Quality validation warning: %s", summary_msg)
            else:
                # TAG mode — attach quality metadata; pass-through
                if hasattr(data, "schema_metadata") and isinstance(
                    data.schema_metadata, dict
                ):
                    data.schema_metadata["quality_report"] = {
                        "passed": False,
                        "failed_checks": [c.expectation_name for c in failed_checks],
                    }

        return data


__all__ = ["QualityValidator"]

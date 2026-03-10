"""Data quality expectations — engine-agnostic validators.

Each :class:`BaseExpectation` automatically dispatches to either
:meth:`validate_pandas` or :meth:`validate_spark` based on the type of the
DataFrame passed to :meth:`validate`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from aptdata.plugins.quality.report import CheckResult, CheckStatus


def _is_spark_df(df: Any) -> bool:
    """Return ``True`` when *df* looks like a PySpark DataFrame."""
    return "pyspark" in type(df).__module__


class BaseExpectation(ABC):
    """Abstract base for all data quality expectations.

    Subclasses implement :meth:`validate_pandas` and :meth:`validate_spark`.
    The concrete :meth:`validate` method dispatches automatically.
    """

    @abstractmethod
    def validate_pandas(self, df: Any) -> CheckResult:
        """Validate a ``pd.DataFrame`` and return a :class:`CheckResult`."""

    @abstractmethod
    def validate_spark(self, df: Any) -> CheckResult:
        """Validate a PySpark ``DataFrame`` and return a :class:`CheckResult`."""

    def validate(self, df: Any) -> CheckResult:
        """Validate *df* dispatching to the appropriate engine implementation."""
        if _is_spark_df(df):
            return self.validate_spark(df)
        return self.validate_pandas(df)


@dataclass
class ExpectColumnToNotBeNull(BaseExpectation):
    """Expect that a column contains no null values.

    Parameters
    ----------
    column:
        Name of the column to check.
    """

    column: str

    def validate_pandas(self, df: Any) -> CheckResult:
        """Check for null values using pandas."""
        if self.column not in df.columns:
            return CheckResult(
                expectation_name="ExpectColumnToNotBeNull",
                column=self.column,
                status=CheckStatus.FAILED,
                message=f"Column '{self.column}' not found in DataFrame.",
                rows_evaluated=len(df),
                rows_failed=len(df),
            )
        null_count = int(df[self.column].isnull().sum())
        status = CheckStatus.PASSED if null_count == 0 else CheckStatus.FAILED
        return CheckResult(
            expectation_name="ExpectColumnToNotBeNull",
            column=self.column,
            status=status,
            message=(
                f"Column '{self.column}' has {null_count} null value(s)."
                if null_count > 0
                else f"Column '{self.column}' has no null values."
            ),
            rows_evaluated=len(df),
            rows_failed=null_count,
        )

    def validate_spark(self, df: Any) -> CheckResult:
        """Check for null values using PySpark."""
        from pyspark.sql import functions as F  # noqa: N812

        total = df.count()
        null_count = df.filter(F.col(self.column).isNull()).count()
        status = CheckStatus.PASSED if null_count == 0 else CheckStatus.FAILED
        return CheckResult(
            expectation_name="ExpectColumnToNotBeNull",
            column=self.column,
            status=status,
            message=(
                f"Column '{self.column}' has {null_count} null value(s)."
                if null_count > 0
                else f"Column '{self.column}' has no null values."
            ),
            rows_evaluated=total,
            rows_failed=null_count,
        )


@dataclass
class ExpectColumnValuesInRange(BaseExpectation):
    """Expect that all values in a column fall within [min_val, max_val].

    Parameters
    ----------
    column:
        Name of the column to check.
    min_val:
        Inclusive lower bound.
    max_val:
        Inclusive upper bound.
    """

    column: str
    min_val: float
    max_val: float

    def validate_pandas(self, df: Any) -> CheckResult:
        """Check numeric range using pandas."""
        if self.column not in df.columns:
            return CheckResult(
                expectation_name="ExpectColumnValuesInRange",
                column=self.column,
                status=CheckStatus.FAILED,
                message=f"Column '{self.column}' not found in DataFrame.",
                rows_evaluated=len(df),
                rows_failed=len(df),
            )
        series = df[self.column]
        out_of_range = int(((series < self.min_val) | (series > self.max_val)).sum())
        status = CheckStatus.PASSED if out_of_range == 0 else CheckStatus.FAILED
        return CheckResult(
            expectation_name="ExpectColumnValuesInRange",
            column=self.column,
            status=status,
            message=(
                f"Column '{self.column}' has {out_of_range} value(s) outside "
                f"[{self.min_val}, {self.max_val}]."
                if out_of_range > 0
                else f"All values in '{self.column}' are within range."
            ),
            rows_evaluated=len(df),
            rows_failed=out_of_range,
            metadata={"min_val": self.min_val, "max_val": self.max_val},
        )

    def validate_spark(self, df: Any) -> CheckResult:
        """Check numeric range using PySpark."""
        from pyspark.sql import functions as F  # noqa: N812

        total = df.count()
        out_of_range = df.filter(
            (F.col(self.column) < self.min_val) | (F.col(self.column) > self.max_val)
        ).count()
        status = CheckStatus.PASSED if out_of_range == 0 else CheckStatus.FAILED
        return CheckResult(
            expectation_name="ExpectColumnValuesInRange",
            column=self.column,
            status=status,
            message=(
                f"Column '{self.column}' has {out_of_range} value(s) outside "
                f"[{self.min_val}, {self.max_val}]."
                if out_of_range > 0
                else f"All values in '{self.column}' are within range."
            ),
            rows_evaluated=total,
            rows_failed=out_of_range,
            metadata={"min_val": self.min_val, "max_val": self.max_val},
        )


@dataclass
class ExpectColumnValuesToBeUnique(BaseExpectation):
    """Expect that all values in a column are unique.

    Parameters
    ----------
    column:
        Name of the column to check.
    """

    column: str

    def validate_pandas(self, df: Any) -> CheckResult:
        """Check uniqueness using pandas."""
        if self.column not in df.columns:
            return CheckResult(
                expectation_name="ExpectColumnValuesToBeUnique",
                column=self.column,
                status=CheckStatus.FAILED,
                message=f"Column '{self.column}' not found in DataFrame.",
                rows_evaluated=len(df),
                rows_failed=len(df),
            )
        duplicates = int(df[self.column].duplicated().sum())
        status = CheckStatus.PASSED if duplicates == 0 else CheckStatus.FAILED
        return CheckResult(
            expectation_name="ExpectColumnValuesToBeUnique",
            column=self.column,
            status=status,
            message=(
                f"Column '{self.column}' has {duplicates} duplicate value(s)."
                if duplicates > 0
                else f"All values in '{self.column}' are unique."
            ),
            rows_evaluated=len(df),
            rows_failed=duplicates,
        )

    def validate_spark(self, df: Any) -> CheckResult:
        """Check uniqueness using PySpark."""
        from pyspark.sql import functions as F  # noqa: N812, F401

        total = df.count()
        unique_count = df.select(self.column).distinct().count()
        duplicates = total - unique_count
        status = CheckStatus.PASSED if duplicates == 0 else CheckStatus.FAILED
        return CheckResult(
            expectation_name="ExpectColumnValuesToBeUnique",
            column=self.column,
            status=status,
            message=(
                f"Column '{self.column}' has {duplicates} duplicate value(s)."
                if duplicates > 0
                else f"All values in '{self.column}' are unique."
            ),
            rows_evaluated=total,
            rows_failed=duplicates,
        )


@dataclass
class ExpectColumnValuesToMatchRegex(BaseExpectation):
    """Expect that all values in a column match a regular expression.

    Parameters
    ----------
    column:
        Name of the column to check.
    pattern:
        Regular expression pattern (Python :mod:`re` syntax).
    """

    column: str
    pattern: str

    def validate_pandas(self, df: Any) -> CheckResult:
        """Check regex match using pandas."""
        if self.column not in df.columns:
            return CheckResult(
                expectation_name="ExpectColumnValuesToMatchRegex",
                column=self.column,
                status=CheckStatus.FAILED,
                message=f"Column '{self.column}' not found in DataFrame.",
                rows_evaluated=len(df),
                rows_failed=len(df),
            )
        series = df[self.column].astype(str)
        non_matching = int((~series.str.match(self.pattern)).sum())
        status = CheckStatus.PASSED if non_matching == 0 else CheckStatus.FAILED
        return CheckResult(
            expectation_name="ExpectColumnValuesToMatchRegex",
            column=self.column,
            status=status,
            message=(
                f"Column '{self.column}' has {non_matching} value(s) not matching "
                f"pattern '{self.pattern}'."
                if non_matching > 0
                else f"All values in '{self.column}' match the pattern."
            ),
            rows_evaluated=len(df),
            rows_failed=non_matching,
            metadata={"pattern": self.pattern},
        )

    def validate_spark(self, df: Any) -> CheckResult:
        """Check regex match using PySpark."""
        from pyspark.sql import functions as F  # noqa: N812

        total = df.count()
        non_matching = df.filter(
            ~F.col(self.column).cast("string").rlike(self.pattern)
        ).count()
        status = CheckStatus.PASSED if non_matching == 0 else CheckStatus.FAILED
        return CheckResult(
            expectation_name="ExpectColumnValuesToMatchRegex",
            column=self.column,
            status=status,
            message=(
                f"Column '{self.column}' has {non_matching} value(s) not matching "
                f"pattern '{self.pattern}'."
                if non_matching > 0
                else f"All values in '{self.column}' match the pattern."
            ),
            rows_evaluated=total,
            rows_failed=non_matching,
            metadata={"pattern": self.pattern},
        )


__all__ = [
    "BaseExpectation",
    "ExpectColumnToNotBeNull",
    "ExpectColumnValuesInRange",
    "ExpectColumnValuesToBeUnique",
    "ExpectColumnValuesToMatchRegex",
]

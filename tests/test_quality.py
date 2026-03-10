"""Tests for data quality plugin — expectations, validator, report, contracts."""

from __future__ import annotations

import warnings

import pytest

pandas = pytest.importorskip("pandas", reason="pandas not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _df(*args, **kwargs):
    import pandas as pd

    return pd.DataFrame(*args, **kwargs)


# ---------------------------------------------------------------------------
# CheckResult & QualityReport
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_defaults(self) -> None:
        from aptdata.plugins.quality.report import CheckResult, CheckStatus

        r = CheckResult(expectation_name="MyExpectation")
        assert r.status == CheckStatus.PASSED
        assert r.rows_evaluated == 0
        assert r.rows_failed == 0
        assert r.column == ""

    def test_custom_values(self) -> None:
        from aptdata.plugins.quality.report import CheckResult, CheckStatus

        r = CheckResult(
            expectation_name="ExpectColumnToNotBeNull",
            column="age",
            status=CheckStatus.FAILED,
            rows_evaluated=100,
            rows_failed=5,
        )
        assert r.status == CheckStatus.FAILED
        assert r.rows_failed == 5


class TestQualityReport:
    def test_passed_all_pass(self) -> None:
        from aptdata.plugins.quality.report import CheckResult, CheckStatus, QualityReport

        report = QualityReport(dataset_uri="memory://test")
        report.checks.append(CheckResult("A", status=CheckStatus.PASSED))
        report.checks.append(CheckResult("B", status=CheckStatus.WARNING))
        assert report.passed is True

    def test_passed_with_failure(self) -> None:
        from aptdata.plugins.quality.report import CheckResult, CheckStatus, QualityReport

        report = QualityReport(dataset_uri="memory://test")
        report.checks.append(CheckResult("A", status=CheckStatus.FAILED))
        assert report.passed is False

    def test_summary_counts(self) -> None:
        from aptdata.plugins.quality.report import CheckResult, CheckStatus, QualityReport

        report = QualityReport(dataset_uri="memory://test")
        report.checks.extend([
            CheckResult("A", status=CheckStatus.PASSED),
            CheckResult("B", status=CheckStatus.PASSED),
            CheckResult("C", status=CheckStatus.FAILED),
            CheckResult("D", status=CheckStatus.WARNING),
        ])
        summary = report.summary
        assert summary[CheckStatus.PASSED] == 2
        assert summary[CheckStatus.FAILED] == 1
        assert summary[CheckStatus.WARNING] == 1

    def test_summary_empty(self) -> None:
        from aptdata.plugins.quality.report import CheckStatus, QualityReport

        report = QualityReport(dataset_uri="memory://test")
        s = report.summary
        assert s[CheckStatus.PASSED] == 0


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


class TestSchemaContract:
    def test_get_pii_columns_by_flag(self) -> None:
        from aptdata.plugins.quality.contract import ColumnContract, SchemaContract

        contract = SchemaContract(
            name="test",
            columns=[
                ColumnContract(name="id", pii=False),
                ColumnContract(name="email", pii=True),
                ColumnContract(name="ssn", pii=True),
            ],
        )
        pii = contract.get_pii_columns()
        assert [c.name for c in pii] == ["email", "ssn"]

    def test_get_pii_columns_by_classification(self) -> None:
        from aptdata.plugins.quality.contract import ColumnClassification, ColumnContract, SchemaContract

        contract = SchemaContract(
            name="test",
            columns=[
                ColumnContract(name="id", pii=False),
                ColumnContract(name="name", classification=ColumnClassification.PII, pii=False),
            ],
        )
        pii = contract.get_pii_columns()
        assert any(c.name == "name" for c in pii)

    def test_get_columns_by_classification(self) -> None:
        from aptdata.plugins.quality.contract import ColumnClassification, ColumnContract, SchemaContract

        contract = SchemaContract(
            name="test",
            columns=[
                ColumnContract(name="a", classification=ColumnClassification.PUBLIC),
                ColumnContract(name="b", classification=ColumnClassification.CONFIDENTIAL),
                ColumnContract(name="c", classification=ColumnClassification.PUBLIC),
            ],
        )
        public = contract.get_columns_by_classification(ColumnClassification.PUBLIC)
        assert [c.name for c in public] == ["a", "c"]

    def test_enforcement_mode_default(self) -> None:
        from aptdata.plugins.quality.contract import EnforcementMode, SchemaContract

        contract = SchemaContract(name="test")
        assert contract.enforcement == EnforcementMode.ABORT


# ---------------------------------------------------------------------------
# Expectations — pandas
# ---------------------------------------------------------------------------


class TestExpectColumnToNotBeNull:
    def test_passes_no_nulls(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnToNotBeNull
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"age": [1, 2, 3]})
        result = ExpectColumnToNotBeNull("age").validate_pandas(df)
        assert result.status == CheckStatus.PASSED
        assert result.rows_failed == 0

    def test_fails_with_nulls(self) -> None:

        from aptdata.plugins.quality.expectations import ExpectColumnToNotBeNull
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"age": [1, None, 3]})
        result = ExpectColumnToNotBeNull("age").validate_pandas(df)
        assert result.status == CheckStatus.FAILED
        assert result.rows_failed == 1

    def test_missing_column(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnToNotBeNull
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"other": [1, 2]})
        result = ExpectColumnToNotBeNull("age").validate_pandas(df)
        assert result.status == CheckStatus.FAILED

    def test_validate_dispatches_to_pandas(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnToNotBeNull
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"x": [1, 2]})
        result = ExpectColumnToNotBeNull("x").validate(df)
        assert result.status == CheckStatus.PASSED


class TestExpectColumnValuesInRange:
    def test_passes_all_in_range(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnValuesInRange
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"score": [0, 50, 100]})
        result = ExpectColumnValuesInRange("score", 0, 100).validate_pandas(df)
        assert result.status == CheckStatus.PASSED

    def test_fails_out_of_range(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnValuesInRange
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"score": [-1, 50, 101]})
        result = ExpectColumnValuesInRange("score", 0, 100).validate_pandas(df)
        assert result.status == CheckStatus.FAILED
        assert result.rows_failed == 2

    def test_metadata_contains_bounds(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnValuesInRange

        df = _df({"score": [5]})
        result = ExpectColumnValuesInRange("score", 0, 10).validate_pandas(df)
        assert result.metadata["min_val"] == 0
        assert result.metadata["max_val"] == 10


class TestExpectColumnValuesToBeUnique:
    def test_passes_unique_values(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnValuesToBeUnique
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"id": [1, 2, 3]})
        result = ExpectColumnValuesToBeUnique("id").validate_pandas(df)
        assert result.status == CheckStatus.PASSED

    def test_fails_duplicate_values(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnValuesToBeUnique
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"id": [1, 1, 2]})
        result = ExpectColumnValuesToBeUnique("id").validate_pandas(df)
        assert result.status == CheckStatus.FAILED
        assert result.rows_failed == 1


class TestExpectColumnValuesToMatchRegex:
    def test_passes_all_match(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnValuesToMatchRegex
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"code": ["A1", "B2", "C3"]})
        result = ExpectColumnValuesToMatchRegex("code", r"[A-Z]\d").validate_pandas(df)
        assert result.status == CheckStatus.PASSED

    def test_fails_non_matching(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnValuesToMatchRegex
        from aptdata.plugins.quality.report import CheckStatus

        df = _df({"code": ["A1", "bad!", "C3"]})
        result = ExpectColumnValuesToMatchRegex("code", r"[A-Z]\d").validate_pandas(df)
        assert result.status == CheckStatus.FAILED
        assert result.rows_failed == 1

    def test_metadata_contains_pattern(self) -> None:
        from aptdata.plugins.quality.expectations import ExpectColumnValuesToMatchRegex

        df = _df({"code": ["A1"]})
        result = ExpectColumnValuesToMatchRegex("code", r"[A-Z]\d").validate_pandas(df)
        assert result.metadata["pattern"] == r"[A-Z]\d"


# ---------------------------------------------------------------------------
# QualityValidator
# ---------------------------------------------------------------------------


class TestQualityValidator:
    def test_abort_on_failure(self) -> None:
        from aptdata.plugins.quality.contract import EnforcementMode
        from aptdata.plugins.quality.expectations import ExpectColumnToNotBeNull
        from aptdata.plugins.quality.validator import QualityValidator

        import pandas as pd

        df = pd.DataFrame({"age": [1, None]})
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("age")],
            enforcement=EnforcementMode.ABORT,
        )
        with pytest.raises(ValueError, match="quality"):
            validator.validate(df)

    def test_warn_on_failure(self) -> None:
        from aptdata.plugins.quality.contract import EnforcementMode
        from aptdata.plugins.quality.expectations import ExpectColumnToNotBeNull
        from aptdata.plugins.quality.validator import QualityValidator

        import pandas as pd

        df = pd.DataFrame({"age": [1, None]})
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("age")],
            enforcement=EnforcementMode.WARN,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = validator.validate(df)
        assert result is df  # data passed through
        assert any("quality" in str(w.message).lower() for w in caught)

    def test_tag_on_failure(self) -> None:
        from aptdata.plugins.dataset import InMemoryDataset
        from aptdata.plugins.quality.contract import EnforcementMode
        from aptdata.plugins.quality.expectations import ExpectColumnToNotBeNull
        from aptdata.plugins.quality.validator import QualityValidator

        ds = InMemoryDataset(uri="memory://test", schema_metadata={})
        ds.write([{"age": None}, {"age": 5}])
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("age")],
            enforcement=EnforcementMode.TAG,
        )
        result = validator.validate(ds)
        assert result is ds
        assert "quality_report" in result.schema_metadata
        assert result.schema_metadata["quality_report"]["passed"] is False

    def test_pass_through_on_success(self) -> None:
        from aptdata.plugins.quality.contract import EnforcementMode
        from aptdata.plugins.quality.expectations import ExpectColumnToNotBeNull
        from aptdata.plugins.quality.validator import QualityValidator

        import pandas as pd

        df = pd.DataFrame({"age": [1, 2, 3]})
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("age")],
            enforcement=EnforcementMode.ABORT,
        )
        result = validator.validate(df)
        assert result is df

    def test_multiple_expectations(self) -> None:
        from aptdata.plugins.quality.contract import EnforcementMode
        from aptdata.plugins.quality.expectations import (
            ExpectColumnToNotBeNull,
            ExpectColumnValuesToBeUnique,
        )
        from aptdata.plugins.quality.validator import QualityValidator

        import pandas as pd

        df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        validator = QualityValidator(
            expectations=[
                ExpectColumnToNotBeNull("id"),
                ExpectColumnValuesToBeUnique("id"),
            ],
            enforcement=EnforcementMode.ABORT,
        )
        result = validator.validate(df)
        assert result is df

    def test_validator_name(self) -> None:
        from aptdata.plugins.quality.validator import QualityValidator

        v = QualityValidator(expectations=[], name="MyValidator")
        assert v.name == "MyValidator"

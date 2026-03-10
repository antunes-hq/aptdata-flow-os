# Data Quality

aptdata provides a lightweight data quality layer that works with both
pandas DataFrames and PySpark DataFrames.

---

## Schema Contracts

A :class:`~aptdata.plugins.quality.contract.SchemaContract` declares the
expected shape, types, and sensitivity of a dataset.

```python
from aptdata.plugins.quality import (
    ColumnClassification,
    ColumnContract,
    EnforcementMode,
    SchemaContract,
)

contract = SchemaContract(
    name="orders_v1",
    version="1.0.0",
    owner="data-engineering",
    description="Customer order records.",
    enforcement=EnforcementMode.ABORT,
    columns=[
        ColumnContract(name="id",     dtype="int64",   nullable=False),
        ColumnContract(name="email",  dtype="str",     nullable=False, pii=True,
                       classification=ColumnClassification.PII),
        ColumnContract(name="amount", dtype="float64", nullable=True),
    ],
)

# Helpers
pii_cols   = contract.get_pii_columns()
pii_tagged = contract.get_columns_by_classification(ColumnClassification.PII)
```

### ColumnClassification

| Value          | Description                        |
|----------------|------------------------------------|
| `PUBLIC`       | No restrictions                    |
| `INTERNAL`     | Internal use only                  |
| `CONFIDENTIAL` | Need-to-know basis                 |
| `PII`          | Personally identifiable information |
| `PHI`          | Protected health information       |
| `FINANCIAL`    | Financial data                     |
| `SENSITIVE`    | Generic sensitive data             |

---

## Expectations

Expectations are individual checks that validate a single property of a
column.  They all extend :class:`~aptdata.plugins.quality.expectations.BaseExpectation`
and return a :class:`~aptdata.plugins.quality.report.CheckResult`.

Each expectation has both a `validate_pandas(df)` and a `validate_spark(df)`
implementation.  Call `validate(df)` and the engine is detected automatically.

### Built-in expectations

#### `ExpectColumnToNotBeNull`

```python
from aptdata.plugins.quality import ExpectColumnToNotBeNull

result = ExpectColumnToNotBeNull("age").validate(df)
```

#### `ExpectColumnValuesInRange`

```python
from aptdata.plugins.quality import ExpectColumnValuesInRange

result = ExpectColumnValuesInRange("score", min_val=0, max_val=100).validate(df)
```

#### `ExpectColumnValuesToBeUnique`

```python
from aptdata.plugins.quality import ExpectColumnValuesToBeUnique

result = ExpectColumnValuesToBeUnique("id").validate(df)
```

#### `ExpectColumnValuesToMatchRegex`

```python
from aptdata.plugins.quality import ExpectColumnValuesToMatchRegex

result = ExpectColumnValuesToMatchRegex("code", pattern=r"[A-Z]\d{3}").validate(df)
```

---

## Quality Validator

:class:`~aptdata.plugins.quality.validator.QualityValidator` runs a suite of
expectations and enforces the result according to the configured
:class:`~aptdata.plugins.quality.contract.EnforcementMode`.

```python
from aptdata.plugins.quality import (
    EnforcementMode,
    ExpectColumnToNotBeNull,
    ExpectColumnValuesToBeUnique,
    QualityValidator,
)

validator = QualityValidator(
    expectations=[
        ExpectColumnToNotBeNull("id"),
        ExpectColumnValuesToBeUnique("id"),
        ExpectColumnToNotBeNull("email"),
    ],
    enforcement=EnforcementMode.ABORT,
    name="order_validator",
)

# Compatible with Workflow.add_step()
from aptdata.core.workflow import Workflow

wf = Workflow("quality_pipeline")
wf.add_step(validator.validate)
clean_data = wf.execute(raw_data)
```

### Enforcement Modes

| Mode   | Behaviour                                                   |
|--------|-------------------------------------------------------------|
| `ABORT` | Raises `ValueError` immediately on first failed expectation |
| `WARN`  | Emits a `warnings.warn` and logs, then continues           |
| `TAG`   | Annotates `schema_metadata["quality_report"]` and continues |

---

## Quality Report

After validation a :class:`~aptdata.plugins.quality.report.QualityReport`
is built internally.  Its `passed` property returns `True` only when no check
has a `FAILED` status, and `summary` returns counts per status.

```python
from aptdata.plugins.quality.report import CheckStatus, QualityReport

report = QualityReport(dataset_uri="s3://bucket/data.parquet")
# ... checks appended by validator ...

print(report.passed)    # True / False
print(report.summary)   # {"PASSED": 3, "FAILED": 1, "WARNING": 0}
```

---

## OTel integration

:class:`~aptdata.plugins.quality.validator.QualityValidator` emits an OTel
span with the following attributes:

| Attribute                                | Description           |
|------------------------------------------|-----------------------|
| `aptdata.quality.validator_name`      | Validator name        |
| `aptdata.quality.enforcement`         | Enforcement mode      |
| `aptdata.quality.num_expectations`    | Number of expectations |
| `aptdata.quality.passed`              | Overall result        |
| `aptdata.quality.num_checks`          | Total checks run      |
| `aptdata.quality.failed_checks`       | Number of failures    |

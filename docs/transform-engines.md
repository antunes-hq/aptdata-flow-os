# Transform Engines

aptdata provides **engine-agnostic transformation wrappers** that integrate
with the :class:`~aptdata.core.workflow.Workflow` pipeline, emit OpenTelemetry
spans, and work transparently with
:class:`~aptdata.plugins.dataset.InMemoryDataset`.

Both transformers are in `aptdata.plugins.transform` and require an optional
dependency group:

```bash
# pandas
pip install pandas

# pyspark
pip install pyspark
```

---

## PandasTransformer

:class:`~aptdata.plugins.transform.pandas.PandasTransformer` wraps any
callable `(pd.DataFrame) → pd.DataFrame` and handles input/output conversion
automatically.

### Constructor

| Parameter       | Type                                           | Description                         |
|-----------------|------------------------------------------------|-------------------------------------|
| `name`          | `str`                                          | Human-readable identifier           |
| `transform_func`| `Callable[[pd.DataFrame], pd.DataFrame]`       | Transformation function             |

### Supported input types

| Input                 | Behaviour                                     |
|-----------------------|-----------------------------------------------|
| `InMemoryDataset`     | Converted to DataFrame; result returned as `InMemoryDataset` |
| `pd.DataFrame`        | Used directly; result is a `pd.DataFrame`     |
| `list[dict]`          | Converted to DataFrame; result is a `pd.DataFrame` |

### OTel span attributes

| Attribute                                | Description               |
|------------------------------------------|---------------------------|
| `aptdata.transformer.name`            | Transformer name          |
| `aptdata.transformer.engine`          | `"pandas"`                |
| `aptdata.transformer.rows_in`         | Input row count           |
| `aptdata.transformer.rows_out`        | Output row count          |
| `aptdata.transformer.columns_out`     | Output column names       |
| `aptdata.transformer.compute_time_ms` | Wall-clock time (ms)      |

### Example

```python
import pandas as pd
from aptdata.plugins.transform import PandasTransformer
from aptdata.core.workflow import Workflow

def clean(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna().drop_duplicates()

transformer = PandasTransformer("clean", clean)

wf = Workflow("my_pipeline")
wf.add_step(transformer.transform)
result = wf.execute(my_dataset)
```

---

## PySparkTransformer

:class:`~aptdata.plugins.transform.spark.PySparkTransformer` wraps a
callable `(SparkSession, DataFrame) → DataFrame`.

### Constructor

| Parameter       | Type                                                   | Description             |
|-----------------|--------------------------------------------------------|-------------------------|
| `name`          | `str`                                                  | Human-readable name     |
| `transform_func`| `Callable[[SparkSession, DataFrame], DataFrame]`       | Transformation function |
| `app_name`      | `str`                                                  | Spark app name          |

### OTel span attributes

All attributes from `PandasTransformer` plus:

| Attribute                    | Description              |
|------------------------------|--------------------------|
| `aptdata.spark.app_name`  | Spark application name   |
| `aptdata.spark.ui_url`    | Spark UI URL (if available) |

### Example

```python
from pyspark.sql import functions as F
from aptdata.plugins.transform import PySparkTransformer
from aptdata.core.workflow import Workflow

def compute_revenue(spark, df):
    return df.withColumn("revenue", F.col("price") * F.col("quantity"))

transformer = PySparkTransformer("compute_revenue", compute_revenue, app_name="ETL")

wf = Workflow("spark_pipeline")
wf.add_step(transformer.transform)
result = wf.execute(spark_df)
```

---

## Workflow integration

Both transformers implement :class:`~aptdata.plugins.base.BaseTransformer`
and are compatible with :meth:`~aptdata.core.workflow.Workflow.add_step`:

```mermaid
flowchart LR
    DS["Dataset\n(InMemoryDataset)"]
    PT["PandasTransformer\nor PySparkTransformer"]
    QV["QualityValidator\n(optional)"]
    OUT["Transformed Dataset"]

    DS --> PT --> QV --> OUT
```

```python
wf = Workflow("full_pipeline")
wf.add_step(pandas_transformer.transform)
wf.add_step(quality_validator.validate)   # see quality docs
result = wf.execute(dataset)
```

---

## Lazy imports

Neither pandas nor pyspark is required at import time.  A
:class:`~aptdata.plugins.manager.PluginDependencyError` is raised only at
instantiation time if the required library is missing.

```python
# This import always succeeds, even without pandas/pyspark installed:
from aptdata.plugins.transform import PandasTransformer, PySparkTransformer
```

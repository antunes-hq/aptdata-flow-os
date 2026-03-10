# DIYs & Snippets

Welcome to the **DIY (Do It Yourself)** section! Here you will find copy-pasteable snippets and mini-tutorials for solving common data engineering problems using **aptdata**.

---

## 1. Minimal Data Transformer with Pandas

Often you just want to take an existing `pandas.DataFrame`, clean it up, and return it. Using `PandasTransformer`, you can wrap simple functions directly into an `aptdata` component.

```python title="clean_data.py"
import pandas as pd
from pydantic.dataclasses import dataclass
from aptdata.core import BaseDataset, IDataset
from aptdata.plugins.transform import PandasTransformer

@dataclass
class DataFrameDataset(BaseDataset):
    """A simple dataset holding a pandas DataFrame."""
    _data: pd.DataFrame = None

    def read(self) -> pd.DataFrame:
        return self._data

    def write(self, data: pd.DataFrame):
        self._data = data

# 1. Define your standard pandas logic
def drop_nulls_and_dedup(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna().drop_duplicates()

# 2. Wrap it with PandasTransformer
transformer = PandasTransformer("clean_data", drop_nulls_and_dedup)

# 3. Use it!
raw_df = pd.DataFrame({"id": [1, 2, 2, None], "value": ["A", "B", "B", "C"]})
dataset = DataFrameDataset(uri="memory://raw")
dataset.write(raw_df)

# Output dataset
result = transformer.transform(dataset)
print(result.read())
```

---

## 2. Enforcing Schema Contracts

This snippet shows how to enforce that a dataset contains no nulls on a primary key column before proceeding to the next step. If it fails, execution aborts.

```python title="quality_check.py"
import pandas as pd
from aptdata.plugins.quality import (
    EnforcementMode, ExpectColumnToNotBeNull, QualityValidator
)

# Set up validation rules
validator = QualityValidator(
    expectations=[ExpectColumnToNotBeNull("id")],
    enforcement=EnforcementMode.ABORT, # Fail fast!
)

raw_df = pd.DataFrame({"id": [1, 2, None], "value": ["A", "B", "C"]})

try:
    clean_data = validator.validate(raw_df)
except ValueError as e:
    print(f"Validation failed: {e}")
```

---

## 3. Emitting Lineage Data

Tracking where data comes from and where it goes is crucial for governance. Here is how you can use `LineageGraph` to emit basic lineage data.

```python title="lineage.py"
from aptdata.core.lineage import LineageGraph, LineageNode, LineageEventType
from aptdata.plugins.governance import LineageStore

# 1. Initialize a Graph for a specific run
graph = LineageGraph(run_id="run-1024", workflow_name="daily_etl")

# 2. Record read and write events
graph.add_node(LineageNode(dataset_uri="s3://bronze/sales", event_type=LineageEventType.READ))
graph.add_node(LineageNode(dataset_uri="s3://silver/sales_clean", event_type=LineageEventType.WRITE))

# 3. Save it to your store (defaults to logging/memory)
store = LineageStore()
store.save(graph)

print("Lineage recorded successfully.")
```

---

## Run from your Browser

Want to try `aptdata` without installing anything? You can run a sandbox environment directly in your browser using Google Colab!

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/strondata/smart-data/blob/main/docs/notebooks/aptdata_quickstart.ipynb)

> **Note:** The Colab notebook will automatically install `aptdata` using `pip install aptdata` inside the environment so you can run the code snippets above immediately.

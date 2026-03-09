"""Transform plugin package — engine-agnostic transformation wrappers.

Provides :class:`PandasTransformer` and :class:`PySparkTransformer` as
concrete :class:`~smart_data.plugins.base.BaseTransformer` implementations.
Both use lazy imports so the framework core works without pandas or pyspark
installed.
"""

from __future__ import annotations

from smart_data.plugins.transform.pandas import PandasTransformer
from smart_data.plugins.transform.spark import PySparkTransformer

__all__ = ["PandasTransformer", "PySparkTransformer"]

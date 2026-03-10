"""Transform plugin package — engine-agnostic transformation wrappers.

Provides :class:`PandasTransformer` and :class:`PySparkTransformer` as
concrete :class:`~aptdata.plugins.base.BaseTransformer` implementations.
Both use lazy imports so the framework core works without pandas or pyspark
installed.
"""

from __future__ import annotations

from aptdata.plugins.transform.pandas import PandasTransformer
from aptdata.plugins.transform.spark import PySparkTransformer

__all__ = ["PandasTransformer", "PySparkTransformer"]

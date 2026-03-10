"""PySpark-based data transformer.

Uses lazy imports so that the framework core works even when pyspark is not
installed.  A :class:`~aptdata.plugins.manager.PluginDependencyError` is
raised at instantiation time if pyspark is not available.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from aptdata.plugins.base import BaseTransformer
from aptdata.plugins.manager import PluginDependencyError
from aptdata.telemetry.instrumentation import get_tracer


class PySparkTransformer(BaseTransformer):
    """Engine-agnostic transformer backed by a PySpark callable.

    Parameters
    ----------
    name:
        Human-readable identifier for this transformer.
    transform_func:
        A callable ``(SparkSession, DataFrame) -> DataFrame`` that applies
        the desired transformation.
    app_name:
        Spark application name passed to ``SparkSession.builder``.

    Examples
    --------
    ::

        from aptdata.plugins.transform import PySparkTransformer

        def double_values(spark, df):
            from pyspark.sql import functions as F
            return df.withColumn("value", F.col("value") * 2)

        transformer = PySparkTransformer("double_values", double_values)
        result = transformer.transform(my_df)
    """

    def __init__(
        self,
        name: str,
        transform_func: Callable[[Any, Any], Any],
        app_name: str = "SmartData",
    ) -> None:
        try:
            import pyspark  # noqa: F401
        except ImportError as exc:
            raise PluginDependencyError("PySparkTransformer", "pyspark") from exc
        self._name = name
        self._transform_func = transform_func
        self._app_name = app_name

    @property
    def name(self) -> str:
        """Human-readable name of this transformer."""
        return self._name

    def transform(self, data: Any) -> Any:
        """Apply the transformation to *data*.

        Parameters
        ----------
        data:
            Accepts a PySpark ``DataFrame``, a ``list[dict]``, or an
            :class:`~aptdata.plugins.dataset.InMemoryDataset`.

        Returns
        -------
        Any
            The transformed PySpark ``DataFrame``.
        """
        from pyspark.sql import SparkSession

        from pyspark.sql.types import StructType

        from aptdata.plugins.dataset import InMemoryDataset

        spark: Any = SparkSession.builder.appName(self._app_name).getOrCreate()

        # Convert input to a PySpark DataFrame if needed.
        if isinstance(data, InMemoryDataset):
            records = data.read()
            df = spark.createDataFrame(records) if records else spark.createDataFrame([], StructType([]))
        elif isinstance(data, list):
            df = spark.createDataFrame(data) if data else spark.createDataFrame([], StructType([]))
        else:
            # Assume it's already a PySpark DataFrame.
            df = data

        rows_in = df.count()

        tracer = get_tracer("aptdata.transform")
        with tracer.start_as_current_span(self._name) as span:
            span.set_attribute("aptdata.transformer.name", self._name)
            span.set_attribute("aptdata.transformer.engine", "pyspark")
            span.set_attribute("aptdata.transformer.rows_in", rows_in)
            span.set_attribute("aptdata.spark.app_name", self._app_name)

            # Try to capture Spark UI URL.
            try:
                ui_url = spark.sparkContext.uiWebUrl
                if ui_url:
                    span.set_attribute("aptdata.spark.ui_url", ui_url)
            except Exception:  # noqa: BLE001
                pass

            t0 = time.perf_counter()
            result_df = self._transform_func(spark, df)
            compute_time_ms = (time.perf_counter() - t0) * 1000.0

            rows_out = result_df.count()
            span.set_attribute("aptdata.transformer.rows_out", rows_out)
            span.set_attribute(
                "aptdata.transformer.compute_time_ms", round(compute_time_ms, 3)
            )

        return result_df


__all__ = ["PySparkTransformer"]

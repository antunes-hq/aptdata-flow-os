"""Pandas-based data transformer.

Uses lazy imports so that the framework core works even when pandas is not
installed.  A :class:`~aptdata.plugins.manager.PluginDependencyError` is
raised at instantiation time if pandas is not available.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from aptdata.core.context import ExecutionContext, IContext
from aptdata.core.dataset import IDataset, PydanticDataset
from aptdata.core.system import BaseComponent
from aptdata.plugins.base import BaseTransformer
from aptdata.plugins.dataset import InMemoryDataset
from aptdata.plugins.manager import PluginDependencyError
from aptdata.telemetry.instrumentation import get_tracer

if TYPE_CHECKING:
    import pandas as pd


class PandasTransformer(BaseTransformer):
    """Engine-agnostic transformer backed by a pandas callable.

    Parameters
    ----------
    name:
        Human-readable identifier for this transformer.
    transform_func:
        A callable ``(pd.DataFrame) -> pd.DataFrame`` that applies the
        desired transformation.

    Examples
    --------
    ::

        from aptdata.plugins.transform import PandasTransformer

        def double_values(df):
            return df.assign(value=df["value"] * 2)

        transformer = PandasTransformer("double_values", double_values)
        result = transformer.transform(my_dataset)
    """

    def __init__(
        self,
        name: str,
        transform_func: Callable[[Any], Any],
    ) -> None:
        try:
            import pandas  # noqa: F401
        except ImportError as exc:
            raise PluginDependencyError("PandasTransformer", "pandas") from exc
        self._name = name
        self._transform_func = transform_func

    @property
    def name(self) -> str:
        """Human-readable name of this transformer."""
        return self._name

    def transform(self, data: Any) -> Any:
        """Apply the transformation to *data*.

        Parameters
        ----------
        data:
            Accepts a :class:`~aptdata.plugins.dataset.InMemoryDataset`,
            a ``pd.DataFrame``, or a ``list[dict]``.

        Returns
        -------
        Any
            The transformed result.  If the input was an
            :class:`~aptdata.plugins.dataset.InMemoryDataset` the output
            will also be one; otherwise a ``pd.DataFrame`` is returned.
        """
        import pandas as pd

        from aptdata.plugins.dataset import InMemoryDataset

        return_dataset = False
        original_uri = "memory://transformed"
        original_schema: dict[str, Any] = {}

        if isinstance(data, InMemoryDataset):
            return_dataset = True
            original_uri = data.uri
            original_schema = data.schema_metadata
            df: pd.DataFrame = pd.DataFrame(data.read())
        elif isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data] if data is not None else [])

        rows_in = len(df)

        tracer = get_tracer("aptdata.transform")
        with tracer.start_as_current_span(self._name) as span:
            span.set_attribute("aptdata.transformer.name", self._name)
            span.set_attribute("aptdata.transformer.engine", "pandas")
            span.set_attribute("aptdata.transformer.rows_in", rows_in)

            t0 = time.perf_counter()
            result_df: pd.DataFrame = self._transform_func(df)
            compute_time_ms = (time.perf_counter() - t0) * 1000.0

            rows_out = len(result_df)
            columns_out = list(result_df.columns)
            span.set_attribute("aptdata.transformer.rows_out", rows_out)
            span.set_attribute("aptdata.transformer.columns_out", str(columns_out))
            span.set_attribute(
                "aptdata.transformer.compute_time_ms", round(compute_time_ms, 3)
            )

        if return_dataset:
            out_dataset = InMemoryDataset(
                uri=original_uri, schema_metadata=original_schema
            )
            out_dataset.write(result_df.to_dict(orient="records"))
            return out_dataset

        return result_df


class PandasTransformComponent(BaseComponent):
    """Component for executing pandas transformations in a Flow.

    Subclasses should implement the `transform` method.
    """

    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return True

    def transform(self, df: "pd.DataFrame", context: IContext) -> "pd.DataFrame":
        """Apply business logic to the dataframe."""
        raise NotImplementedError

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        try:
            import pandas as pd
        except ImportError as exc:
            raise PluginDependencyError("PandasTransformComponent", "pandas") from exc

        # Read datasets into a single dataframe, or handle them appropriately.
        # For simplicity in linear flow, we merge or take the first.
        if not inputs:
            df = pd.DataFrame()
        else:
            dfs = []
            for ds in inputs:
                data = ds.read()
                if isinstance(data, pd.DataFrame):
                    dfs.append(data)
                elif isinstance(data, list):
                    dfs.append(pd.DataFrame(data))
                else:
                    dfs.append(pd.DataFrame([data] if data is not None else []))
            df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

        # Execute business logic
        context = ExecutionContext()
        result_df = self.transform(df, context)

        # Encapsulate back into an IDataset
        # Usually BaseFlow wraps this in a PydanticDataset if output_contract is provided.
        # Otherwise, fallback to an InMemoryDataset
        out_ds = InMemoryDataset(uri=f"memory://{self.component_id}_output")
        out_ds.write(result_df.to_dict(orient="records"))

        return [out_ds]

__all__ = ["PandasTransformer", "PandasTransformComponent"]

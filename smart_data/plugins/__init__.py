"""Plugin registry for smart-data pipelines.

Third-party adapters (Spark, REST APIs, databases, …) register concrete
implementations of :class:`~smart_data.core.pipeline.IPipeline` here
so that the CLI can discover and instantiate them by name.

Usage
-----
Register a pipeline::

    from smart_data.plugins import registry
    from my_package import MyPipeline

    registry.register("my_pipeline", MyPipeline)

Look up a pipeline by name::

    pipeline_cls = registry.get("my_pipeline")
    if pipeline_cls is not None:
        pipeline_cls().run()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from smart_data.core.pipeline import IPipeline


class _PipelineRegistry:
    """Simple name → pipeline-class mapping."""

    def __init__(self) -> None:
        self._store: dict[str, type[IPipeline]] = {}

    def register(self, name: str, pipeline_cls: type[IPipeline]) -> None:
        """Register *pipeline_cls* under *name*.

        Parameters
        ----------
        name:
            Unique identifier used on the CLI (e.g. ``"pipeline_x"``).
        pipeline_cls:
            A concrete subclass of :class:`~smart_data.core.pipeline.IPipeline`.
        """
        self._store[name] = pipeline_cls

    def get(self, name: str) -> type[IPipeline] | None:
        """Return the pipeline class registered under *name*, or ``None``."""
        return self._store.get(name)

    def list_pipelines(self) -> list[str]:
        """Return a sorted list of all registered pipeline names."""
        return sorted(self._store)


#: Global singleton registry – import this in adapter modules.
registry = _PipelineRegistry()

__all__ = ["registry", "_PipelineRegistry"]

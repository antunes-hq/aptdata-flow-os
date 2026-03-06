"""Abstract pipeline contract."""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from smart_data.core.step import AbstractStep


class AbstractPipeline(BaseModel, ABC):
    """Abstract base class for all pipelines.

    A pipeline orchestrates a directed acyclic graph (DAG) of
    :class:`AbstractStep` instances.  Concrete implementations must
    register steps, compile the execution graph and provide a ``run``
    entry-point.
    """

    model_config = {"arbitrary_types_allowed": True}

    @abstractmethod
    def register_step(self, step: AbstractStep) -> None:
        """Register a step into the pipeline."""

    @abstractmethod
    def compile_dag(self) -> None:
        """Compile and validate the DAG before execution."""

    @abstractmethod
    def run(self) -> None:
        """Execute the compiled pipeline."""

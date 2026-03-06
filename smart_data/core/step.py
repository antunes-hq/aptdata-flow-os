"""Step interface and base class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic.dataclasses import dataclass as pydantic_dataclass

from smart_data.core.dataset import BaseDataset, IDataset


@dataclass
class IStep(ABC):
    """Dataclass interface for pipeline step types.

    A step represents a single, reusable unit of work.  It receives a list
    of :class:`~smart_data.core.dataset.IDataset` inputs, validates them and
    produces one :class:`~smart_data.core.dataset.IDataset` output.
    """

    @abstractmethod
    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        """Validate the step inputs before execution.

        Returns ``True`` when inputs are valid, ``False`` otherwise.
        """

    @abstractmethod
    def execute(self, inputs: list[IDataset]) -> IDataset:
        """Execute the step logic and return the resulting dataset."""


@pydantic_dataclass
class BaseStep(IStep):
    """Base pipeline step with a Pydantic-validated ``step_id`` field.

    Concrete step implementations must inherit from this class and
    implement the :meth:`validate_inputs` and :meth:`execute` abstract
    methods inherited from :class:`IStep`.
    """

    step_id: str

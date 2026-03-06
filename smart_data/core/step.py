"""Abstract step contract."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from smart_data.core.dataset import AbstractDataset


class AbstractStep(BaseModel, ABC):
    """Abstract base class for all pipeline steps.

    A step encapsulates a single, reusable unit of work.  It receives a
    list of :class:`AbstractDataset` inputs, validates them and produces
    one :class:`AbstractDataset` output.
    """

    step_id: str

    model_config = {"arbitrary_types_allowed": True}

    @abstractmethod
    def validate_inputs(self, inputs: list[AbstractDataset]) -> bool:
        """Validate the step inputs before execution.

        Returns ``True`` when inputs are valid, ``False`` otherwise.
        """

    @abstractmethod
    def execute(self, inputs: list[AbstractDataset]) -> AbstractDataset:
        """Execute the step logic and return the resulting dataset."""

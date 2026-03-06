"""Abstract dataset contract."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AbstractDataset(BaseModel, ABC):
    """Abstract base class for all datasets.

    Combines Pydantic validation with ABC enforcement so that
    every concrete dataset declares its URI, carries schema
    metadata and implements both read and write operations.
    """

    uri: str
    schema_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    @abstractmethod
    def read(self) -> Any:
        """Read and return data from the dataset."""

    @abstractmethod
    def write(self, data: Any) -> None:
        """Write data to the dataset."""

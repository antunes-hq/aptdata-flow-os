"""Dataset interface and base class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic.dataclasses import dataclass as pydantic_dataclass


@dataclass
class IDataset(ABC):
    """Dataclass interface for dataset types.

    All dataset contracts must implement :meth:`read` and :meth:`write`.
    No concrete fields are defined here – field declarations live in
    :class:`BaseDataset` and its subclasses.
    """

    @abstractmethod
    def read(self) -> Any:
        """Read and return data from the dataset."""

    @abstractmethod
    def write(self, data: Any) -> None:
        """Write data to the dataset."""


@pydantic_dataclass
class BaseDataset(IDataset):
    """Base dataset with Pydantic-validated fields.

    Provides the canonical ``uri`` and ``schema_metadata`` fields.
    Concrete dataset implementations must inherit from this class and
    implement the :meth:`read` and :meth:`write` abstract methods
    inherited from :class:`IDataset`.
    """

    uri: str
    schema_metadata: dict[str, Any] = field(default_factory=dict)

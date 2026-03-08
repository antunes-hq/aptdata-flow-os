"""Abstract base interfaces for plugin readers and writers.

Every concrete reader / writer must subclass :class:`BaseReader` or
:class:`BaseWriter` and implement the corresponding abstract method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from smart_data.core.dataset import BaseDataset


class BaseReader(ABC):
    """Interface for reading data from an external source.

    Subclasses **must** implement :meth:`read` and return a
    :class:`~smart_data.core.dataset.BaseDataset` (or compatible subclass).
    """

    @abstractmethod
    def read(self, **kwargs: Any) -> BaseDataset:
        """Read data from the source and return a :class:`BaseDataset`."""


class BaseWriter(ABC):
    """Interface for writing a dataset to an external target.

    Subclasses **must** implement :meth:`write`.
    """

    @abstractmethod
    def write(self, dataset: BaseDataset, **kwargs: Any) -> None:
        """Persist *dataset* to the target."""


__all__ = ["BaseReader", "BaseWriter"]

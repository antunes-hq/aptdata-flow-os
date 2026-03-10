"""Abstract base interfaces for plugin readers, writers, and transformers.

Every concrete reader / writer / transformer must subclass :class:`BaseReader`,
:class:`BaseWriter`, or :class:`BaseTransformer` and implement the corresponding
abstract method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aptdata.core.dataset import BaseDataset


class BaseReader(ABC):
    """Interface for reading data from an external source.

    Subclasses **must** implement :meth:`read` and return a
    :class:`~aptdata.core.dataset.BaseDataset` (or compatible subclass).
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


class BaseTransformer(ABC):
    """Interface for transforming data using an engine-specific implementation.

    Subclasses **must** implement :attr:`name` and :meth:`transform`.
    Transformer instances are compatible with :meth:`Workflow.add_step` —
    pass ``transformer.transform`` as the step callable.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name identifying this transformer."""

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """Apply the transformation to *data* and return the result."""


__all__ = ["BaseReader", "BaseWriter", "BaseTransformer"]

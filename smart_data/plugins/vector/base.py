"""Base abstractions for vector DB writers."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from smart_data.core.dataset import BaseDataset
from smart_data.plugins.base import BaseWriter


class VectorWriter(BaseWriter):
    """Base writer for vector databases."""

    @abstractmethod
    def write(self, dataset: BaseDataset, **kwargs: Any) -> None:  # pragma: no cover - interface only
        """Persist vectors from *dataset* into the destination vector store."""

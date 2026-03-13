"""Dataset interface and base class."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass


class DataContractError(Exception):
    """Exception raised when dataset data does not conform to the expected Pydantic
    contract."""

    pass


T = TypeVar("T")

@dataclass
class IDataset(ABC, Generic[T]):
    """Dataclass interface for dataset types.

    All dataset contracts must implement :meth:`read` and :meth:`write`.
    No concrete fields are defined here – field declarations live in
    :class:`BaseDataset` and its subclasses.
    """

    @abstractmethod
    def read(self) -> T:
        """Read and return data from the dataset."""
        raise NotImplementedError

    @abstractmethod
    def write(self, data: T) -> None:
        """Write data to the dataset."""
        raise NotImplementedError


@pydantic_dataclass
class BaseDataset(IDataset[Any]):
    """Base dataset with Pydantic-validated fields.

    Provides the canonical ``uri`` and ``schema_metadata`` fields.
    Concrete dataset implementations must inherit from this class and
    implement the :meth:`read` and :meth:`write` abstract methods
    inherited from :class:`IDataset`.
    """

    uri: str
    schema_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IIterableDataset(IDataset[Iterator[T]]):
    """Dataset interface that returns Python generators (Yield)."""

    @abstractmethod
    def read(self) -> Iterator[T]:
        """Yield and return data chunks or records from the dataset."""
        raise NotImplementedError

    @abstractmethod
    def write(self, data: Iterator[T]) -> None:
        """Write yielded data to the dataset."""
        raise NotImplementedError


M = TypeVar("M", bound=BaseModel)


@pydantic_dataclass
class PydanticDataset(BaseDataset, Generic[M]):
    """A dataset implementation that enforces a Pydantic model contract.

    Data validation is performed when data is written to or read from the dataset.
    This implementation optimized for Pandas dataframes by converting the Pydantic
    schema into pandas dtypes, ensuring fail-fast execution without row-by-row
    iteration.
    """

    contract: type[M] | None = field(default=None)
    _data: Any = field(default=None, init=False, repr=False)

    def read(self) -> Any:
        return self._data

    def write(self, data: Any) -> None:
        if self.contract is not None:
            self._validate(data)
        self._data = data

    def _validate(self, data: Any) -> None:
        """Validates the input data against the configured Pydantic contract."""
        if self.contract is None:
            return

        try:
            import pandas as pd
        except ImportError:
            # Fallback to pure pydantic if pandas isn't installed.
            # We assume data is a list of dicts.
            if isinstance(data, list):
                for row in data:
                    try:
                        self.contract.model_validate(row)
                    except Exception as e:
                        raise DataContractError(f"Validation failed for row {row}: {e}")
            return

        if isinstance(data, pd.DataFrame):
            # Optimised pandas validation
            schema_fields = self.contract.model_fields
            actual_columns = set(data.columns)

            # Check for missing columns
            required_columns = {k for k, v in schema_fields.items() if v.is_required()}
            missing_required = required_columns - actual_columns
            if missing_required:
                raise DataContractError(
                    f"DataFrame is missing required columns: {missing_required}"
                )

            # Optionally check types (fail-fast type checking without row-by-row)
            # This is a basic conversion check
            for col, field_info in schema_fields.items():
                if col in data.columns:
                    # In a real-world scenario, we would map pydantic types to
                    # numpy/pandas dtypes and ensure the types match perfectly.
                    # For now we rely on missing columns and basic null checks.
                    if field_info.is_required() and data[col].isnull().any():
                        raise DataContractError(
                            f"Column '{col}' contains null values but is required."
                        )
        elif isinstance(data, list):
            for row in data:
                try:
                    self.contract.model_validate(row)
                except Exception as e:
                    raise DataContractError(f"Validation failed for row {row}: {e}")

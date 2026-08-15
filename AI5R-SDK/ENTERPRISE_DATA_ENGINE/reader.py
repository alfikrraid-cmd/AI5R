from abc import ABC, abstractmethod

from .raw_dataset import RawDataset
from .source_descriptor import SourceDescriptor


class Reader(ABC):
    """Stateless acquisition contract for Enterprise Data Engine readers."""

    __slots__ = ()

    @abstractmethod
    def supports(self, source: SourceDescriptor) -> bool:
        """Return whether this reader can acquire the described source."""

    @abstractmethod
    def read(self, source: SourceDescriptor) -> RawDataset:
        """Acquire and return source data without interpretation."""


__all__ = ["Reader"]

from abc import ABC, abstractmethod

from .detected_enterprise_object import DetectedEnterpriseObjects


class CommitAdapter(ABC):
    """Domain-agnostic transaction boundary for target Enterprise OS writes."""

    @abstractmethod
    def commit(
        self,
        objects: tuple[DetectedEnterpriseObjects, ...],
    ) -> str:
        """Write one descriptor batch and return its transaction identifier."""

    @abstractmethod
    def rollback(self, transaction_id: str) -> bool:
        """Request rollback of a previously committed transaction."""

    @abstractmethod
    def status(self, transaction_id: str) -> str:
        """Return target-owned transaction status."""


__all__ = ["CommitAdapter"]

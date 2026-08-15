from .commit_adapter import CommitAdapter
from .commit_result import CommitResult, CommitStatistics
from .detected_enterprise_object import DetectedEnterpriseObjects
from .import_preview import ImportPreview
from .validation_result import ValidationResult


class CommitEngine:
    """Coordinate an approved descriptor transaction through one adapter."""

    __slots__ = ("_adapter",)

    def __init__(self, adapter: CommitAdapter) -> None:
        if not isinstance(adapter, CommitAdapter):
            raise TypeError("adapter must implement CommitAdapter")
        self._adapter = adapter

    def commit(
        self,
        preview: ImportPreview,
        validation: ValidationResult,
        objects,
        *,
        dry_run: bool = False,
    ) -> CommitResult:
        batch = (
            (objects,)
            if isinstance(objects, DetectedEnterpriseObjects)
            else tuple(objects)
        )
        worksheet_count = len(batch)
        descriptor_count = sum(
            1 + len(item.related_objects) for item in batch
        )

        if not preview.is_valid or not validation.is_valid:
            return CommitResult(
                success=False,
                status="REJECTED",
                transaction_id=None,
                statistics=CommitStatistics(
                    worksheet_count=worksheet_count,
                    descriptor_count=descriptor_count,
                    committed_objects=0,
                    failed_objects=0,
                    dry_run=dry_run,
                ),
                error="Import preview and validation must be valid",
            )

        if dry_run:
            return CommitResult(
                success=True,
                status="DRY_RUN",
                transaction_id=None,
                statistics=CommitStatistics(
                    worksheet_count=worksheet_count,
                    descriptor_count=descriptor_count,
                    committed_objects=0,
                    failed_objects=0,
                    dry_run=True,
                ),
            )

        try:
            transaction_id = self._adapter.commit(batch)
        except Exception as error:
            return CommitResult(
                success=False,
                status="FAILED",
                transaction_id=None,
                statistics=CommitStatistics(
                    worksheet_count=worksheet_count,
                    descriptor_count=descriptor_count,
                    committed_objects=0,
                    failed_objects=descriptor_count,
                    dry_run=False,
                ),
                error=str(error),
            )

        return CommitResult(
            success=True,
            status="COMMITTED",
            transaction_id=transaction_id,
            statistics=CommitStatistics(
                worksheet_count=worksheet_count,
                descriptor_count=descriptor_count,
                committed_objects=descriptor_count,
                failed_objects=0,
                dry_run=False,
            ),
            rollback_available=True,
        )

    def rollback(self, transaction_id: str) -> bool:
        return self._adapter.rollback(transaction_id)

    def status(self, transaction_id: str) -> str:
        return self._adapter.status(transaction_id)

    @staticmethod
    def statistics(result: CommitResult) -> CommitStatistics:
        return result.statistics


__all__ = ["CommitEngine"]

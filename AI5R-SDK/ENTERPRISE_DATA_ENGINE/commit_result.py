from dataclasses import dataclass


@dataclass(frozen=True)
class CommitStatistics:
    worksheet_count: int
    descriptor_count: int
    committed_objects: int
    failed_objects: int
    dry_run: bool


@dataclass(frozen=True)
class CommitResult:
    success: bool
    status: str
    transaction_id: str | None
    statistics: CommitStatistics
    error: str | None = None
    rollback_available: bool = False


__all__ = ["CommitResult", "CommitStatistics"]

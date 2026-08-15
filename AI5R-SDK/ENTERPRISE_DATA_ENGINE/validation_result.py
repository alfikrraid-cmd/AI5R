from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    worksheet_name: str
    column_index: int | None = None


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    issues: tuple[ValidationIssue, ...]
    worksheet_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(self.issues))


__all__ = ["ValidationIssue", "ValidationResult"]

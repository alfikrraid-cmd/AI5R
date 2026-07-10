from __future__ import annotations

from enum import StrEnum, unique


@unique
class ManufacturingStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    PLANNING = "planning"
    PREPARING = "preparing"
    MANUFACTURING = "manufacturing"
    ASSEMBLING = "assembling"
    PACKAGING = "packaging"
    TESTING = "testing"
    RELEASING = "releasing"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def terminal_statuses(cls) -> frozenset["ManufacturingStatus"]:
        return frozenset(
            {
                cls.COMPLETED,
                cls.FAILED,
                cls.CANCELLED,
            }
        )

    @property
    def is_terminal(self) -> bool:
        return self in self.terminal_statuses()

    @property
    def is_active(self) -> bool:
        return not self.is_terminal

    @classmethod
    def from_value(cls, value: str) -> "ManufacturingStatus":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid ManufacturingStatus value: {value!r}"
            ) from exc

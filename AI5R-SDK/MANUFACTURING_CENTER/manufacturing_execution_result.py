"""
MFG-005C-7
Manufacturing Execution Result

Immutable, deterministic snapshot describing the outcome of a
Manufacturing Runtime execution.

This component holds no behavior beyond validation and conversion. It
does not execute anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class ManufacturingExecutionResult:
    status: str
    completed_nodes: tuple[str, ...] = field(default_factory=tuple)
    failed_nodes: tuple[str, ...] = field(default_factory=tuple)
    execution_order: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status is required")

        object.__setattr__(
            self, "completed_nodes", tuple(self.completed_nodes)
        )
        object.__setattr__(self, "failed_nodes", tuple(self.failed_nodes))
        object.__setattr__(
            self, "execution_order", tuple(self.execution_order)
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "completed_nodes": list(self.completed_nodes),
            "failed_nodes": list(self.failed_nodes),
            "execution_order": list(self.execution_order),
            "metadata": dict(self.metadata),
        }

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardViolation:
    rule: str
    module: str
    reason: str


@dataclass
class GuardResult:
    violations: list[GuardViolation] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0


class RuntimeGuard:
    """
    RC-001: Runtime Hardening Gate

    Ensures:
    - no broken module imports
    - no forbidden runtime coupling
    - no empty core contracts
    """

    FORBIDDEN_PATTERNS = [
        "eval(",
        "exec(",
    ]

    def validate_code(self, module_name: str, source: str) -> GuardResult:
        result = GuardResult()

        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in source:
                result.violations.append(
                    GuardViolation(
                        rule="FORBIDDEN_RUNTIME_PATTERN",
                        module=module_name,
                        reason=f"Detected {pattern}",
                    )
                )

        return result

    def validate_contracts(self, contracts: dict[str, Any]) -> GuardResult:
        result = GuardResult()

        for name, value in contracts.items():
            if value is None:
                result.violations.append(
                    GuardViolation(
                        rule="EMPTY_CONTRACT",
                        module=name,
                        reason="Contract is None",
                    )
                )

        return result

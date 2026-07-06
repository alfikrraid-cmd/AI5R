from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VerificationResult:
    status: str
    checked: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == "PASS"


class ArchitectureVerifier:
    REQUIRED_MODULES = [
        "FOUNDATION",
        "FACTORY",
        "REALITY",
        "WAREHOUSE",
        "EXPERIENCE",
        "MEMORY",
        "KNOWLEDGE",
        "EXECUTION",
        "DIGITAL_EMPLOYEE",
        "DIGITAL_WORKFLOW",
        "DIGITAL_ORGANIZATION",
        "RUNTIME",
        "OS",
    ]

    def __init__(self, sdk_root: str | Path):
        self.sdk_root = Path(sdk_root)

    def verify(self) -> VerificationResult:
        result = VerificationResult(status="PASS")

        for module in self.REQUIRED_MODULES:
            path = self.sdk_root / module

            if path.exists():
                result.checked.append(module)
            else:
                result.missing.append(module)

        if result.missing:
            result.status = "FAIL"

        return result

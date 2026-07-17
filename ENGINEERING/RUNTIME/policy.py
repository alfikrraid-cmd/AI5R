from dataclasses import dataclass, field

from .contracts import CapabilityRequest
from .exceptions import PolicyViolation


@dataclass
class RuntimePolicy:
    allowed_capabilities: list[str] = field(default_factory=list)
    readonly: bool = False
    dry_run: bool = False

    def validate(self, request: CapabilityRequest) -> None:
        if request.capability not in self.allowed_capabilities:
            raise PolicyViolation(
                f"Capability not allowed by policy: {request.capability}"
            )

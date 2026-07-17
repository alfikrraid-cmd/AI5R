from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .result import CapabilityResult


@dataclass
class CapabilityRequest:
    capability: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    """Reserved for future runtime information (workspace, user,
    correlation id, runtime metadata). Not read by any runtime logic yet."""


class Capability(ABC):
    """Base contract every engineering capability must implement.

    The runtime only ever calls `execute()`. It never inspects or
    depends on how a capability is implemented internally.
    """

    capability_code: str
    capability_name: str

    @abstractmethod
    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        ...

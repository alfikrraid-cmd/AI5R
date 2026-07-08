from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuntimeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RuntimeRequest:
    profile: str
    definition: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeResponse:
    status: RuntimeStatus
    profile: str
    definition: str
    output: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeEngine:

    engine_name = "AI5R Canonical Runtime Engine"

    def execute(
        self,
        request: RuntimeRequest,
    ) -> RuntimeResponse:

        return RuntimeResponse(
            status=RuntimeStatus.SUCCESS,
            profile=request.profile,
            definition=request.definition,
            output=request.payload,
            metadata=request.metadata,
        )

from collections.abc import Callable
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
    error: str | None = None


RuntimeHandler = Callable[[RuntimeRequest], dict[str, Any]]


class RuntimeEngine:
    engine_name = "AI5R Canonical Runtime Engine"

    def __init__(self):
        self._handlers: dict[tuple[str, str], RuntimeHandler] = {}

    def register_handler(
        self,
        profile: str,
        definition: str,
        handler: RuntimeHandler,
    ) -> None:
        if not profile:
            raise ValueError("profile is required")
        if not definition:
            raise ValueError("definition is required")

        self._handlers[(profile, definition)] = handler

    def has_handler(self, profile: str, definition: str) -> bool:
        return (profile, definition) in self._handlers

    def execute(
        self,
        request: RuntimeRequest,
    ) -> RuntimeResponse:
        handler = self._handlers.get((request.profile, request.definition))

        if handler is None:
            return RuntimeResponse(
                status=RuntimeStatus.SUCCESS,
                profile=request.profile,
                definition=request.definition,
                output=request.payload,
                metadata=request.metadata,
            )

        try:
            output = handler(request)
            return RuntimeResponse(
                status=RuntimeStatus.SUCCESS,
                profile=request.profile,
                definition=request.definition,
                output=output,
                metadata=request.metadata,
            )
        except Exception as exc:
            return RuntimeResponse(
                status=RuntimeStatus.FAILED,
                profile=request.profile,
                definition=request.definition,
                output={},
                metadata=request.metadata,
                error=str(exc),
            )

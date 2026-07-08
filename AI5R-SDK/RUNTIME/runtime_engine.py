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

    def register_capability(
        self,
        profile: str,
        capability_id: str,
        handler: RuntimeHandler,
    ) -> None:
        self.register_handler(
            profile=profile,
            definition=capability_id,
            handler=handler,
        )

    def has_handler(self, profile: str, definition: str) -> bool:
        return (profile, definition) in self._handlers

    def has_capability(self, profile: str, capability_id: str) -> bool:
        return self.has_handler(profile, capability_id)

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

    def execute_pipeline(
        self,
        profile: str,
        definitions: tuple[str, ...],
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeResponse:
        if not definitions:
            raise ValueError("definitions are required")

        current_payload = payload or {}
        current_metadata = metadata or {}

        for definition in definitions:
            response = self.execute(
                RuntimeRequest(
                    profile=profile,
                    definition=definition,
                    payload=current_payload,
                    metadata=current_metadata,
                )
            )

            if response.status == RuntimeStatus.FAILED:
                return response

            current_payload = response.output
            current_metadata = response.metadata

        return RuntimeResponse(
            status=RuntimeStatus.SUCCESS,
            profile=profile,
            definition=definitions[-1],
            output=current_payload,
            metadata=current_metadata,
        )

    def execute_capability_pipeline(
        self,
        profile: str,
        capability_ids: tuple[str, ...],
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeResponse:
        return self.execute_pipeline(
            profile=profile,
            definitions=capability_ids,
            payload=payload,
            metadata=metadata,
        )

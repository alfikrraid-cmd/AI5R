from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OSContext:
    context_id: str
    process_id: str
    scope: str = "PROCESS"
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ContextManager:
    def __init__(self):
        self._contexts: dict[str, OSContext] = {}

    def create_context(
        self,
        process_id: str,
        scope: str = "PROCESS",
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OSContext:
        if not process_id:
            raise ValueError("process_id is required")

        context_id = f"ctx-{process_id}"

        context = OSContext(
            context_id=context_id,
            process_id=process_id,
            scope=scope,
            data=data or {},
            metadata=metadata or {},
        )

        self._contexts[context_id] = context
        return context

    def get_context(self, context_id: str) -> OSContext | None:
        return self._contexts.get(context_id)

    def get_process_context(self, process_id: str) -> OSContext | None:
        return self._contexts.get(f"ctx-{process_id}")

    def update_context(
        self,
        context_id: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OSContext:
        context = self.get_context(context_id)

        if context is None:
            raise ValueError("context not found")

        if data:
            context.data.update(data)

        if metadata:
            context.metadata.update(metadata)

        context.updated_at = datetime.now(timezone.utc).isoformat()
        return context

    def delete_context(self, context_id: str) -> bool:
        if context_id not in self._contexts:
            return False

        del self._contexts[context_id]
        return True

    def list_contexts(self) -> list[OSContext]:
        return list(self._contexts.values())

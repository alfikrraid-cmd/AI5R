from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ContextScope(str, Enum):
    GOAL = "GOAL"
    TASK = "TASK"
    EMPLOYEE = "EMPLOYEE"
    ORGANIZATION = "ORGANIZATION"


@dataclass
class ContextObject:
    context_id: str
    scope: ContextScope
    owner_id: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ContextManager:
    def __init__(self):
        self.contexts: dict[str, ContextObject] = {}

    def create(
        self,
        context_id: str,
        scope: ContextScope,
        owner_id: str,
        data: dict[str, Any] | None = None,
    ) -> ContextObject:
        if not context_id:
            raise ValueError("context_id is required")

        if not owner_id:
            raise ValueError("owner_id is required")

        context = ContextObject(
            context_id=context_id,
            scope=scope,
            owner_id=owner_id,
            data=data or {},
        )

        self.contexts[context_id] = context
        return context

    def get(self, context_id: str) -> ContextObject:
        if context_id not in self.contexts:
            raise KeyError(f"Context not found: {context_id}")

        return self.contexts[context_id]

    def update(
        self,
        context_id: str,
        data: dict[str, Any],
    ) -> ContextObject:
        context = self.get(context_id)
        context.data.update(data)
        context.updated_at = datetime.now(UTC).isoformat()
        return context

    def list_by_owner(self, owner_id: str) -> list[ContextObject]:
        return [
            context
            for context in self.contexts.values()
            if context.owner_id == owner_id
        ]

    def list_by_scope(self, scope: ContextScope) -> list[ContextObject]:
        return [
            context
            for context in self.contexts.values()
            if context.scope == scope
        ]

    def merge(
        self,
        context_ids: list[str],
        merged_context_id: str,
        scope: ContextScope,
        owner_id: str,
    ) -> ContextObject:
        merged_data: dict[str, Any] = {}

        for context_id in context_ids:
            merged_data.update(self.get(context_id).data)

        return self.create(
            context_id=merged_context_id,
            scope=scope,
            owner_id=owner_id,
            data=merged_data,
        )

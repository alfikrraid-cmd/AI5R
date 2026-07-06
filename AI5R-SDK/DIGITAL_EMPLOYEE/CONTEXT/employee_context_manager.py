from __future__ import annotations

from typing import Any

from .employee_context import EmployeeContext


class EmployeeContextManager:
    def __init__(self) -> None:
        self._contexts: dict[str, EmployeeContext] = {}

    def create_context(
        self,
        employee_id: str,
        role: str | None = None,
        department_id: str | None = None,
        organization_id: str | None = None,
        active_goal: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EmployeeContext:
        if not employee_id:
            raise ValueError("Employee ID is required")

        context = EmployeeContext(
            employee_id=employee_id,
            role=role,
            department_id=department_id,
            organization_id=organization_id,
            active_goal=active_goal,
            metadata=metadata or {},
        )
        self._contexts[employee_id] = context
        return context

    def get_context(self, employee_id: str) -> EmployeeContext | None:
        return self._contexts.get(employee_id)

    def require_context(self, employee_id: str) -> EmployeeContext:
        context = self.get_context(employee_id)
        if context is None:
            raise KeyError(f"Employee context not found: {employee_id}")
        return context

    def update_context(self, employee_id: str, **kwargs: Any) -> EmployeeContext:
        context = self.require_context(employee_id)
        return context.update(**kwargs)

    def attach_metadata(
        self,
        employee_id: str,
        key: str,
        value: Any,
    ) -> EmployeeContext:
        context = self.require_context(employee_id)
        return context.attach_metadata(key, value)

    def list_contexts(self) -> list[EmployeeContext]:
        return list(self._contexts.values())

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            employee_id: context.snapshot()
            for employee_id, context in self._contexts.items()
        }

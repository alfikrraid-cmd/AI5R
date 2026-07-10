"""
AO-004
Organization Runtime

Orchestrates RoleAssignment execution sequentially and
deterministically, delegating actual execution to an injected
assignment_executor.

This component does not execute any business logic and never invokes
an LLM. It is independent of the Manufacturing Center; Manufacturing
Center may only be reached indirectly, through an injected
assignment_executor.
"""

from __future__ import annotations

from typing import Any


class OrganizationRuntime:
    """
    Runtime orchestrating RoleAssignment execution.
    """

    def __init__(
        self,
        scheduler: Any = None,
        assignment_executor: Any = None,
    ) -> None:
        self.scheduler = scheduler
        self.assignment_executor = assignment_executor

    def assign(self, assignments: list) -> list:
        """
        Determine the deterministic execution order for assignments.

        Args:
            assignments:
                RoleAssignment objects to order.

        Returns:
            Assignments in deterministic order.
        """
        if not assignments:
            return []

        if self.scheduler is not None:
            return list(self.scheduler.order(assignments))

        return sorted(assignments, key=lambda assignment: assignment.assignment_id)

    def execute(self, assignments: list) -> list:
        """
        Execute assignments sequentially through the injected
        assignment_executor.

        Args:
            assignments:
                RoleAssignment objects to execute.

        Returns:
            RoleExecutionResult objects in deterministic order.
        """
        ordered = self.assign(assignments)

        if not ordered:
            return []

        if self.assignment_executor is None:
            raise ValueError("assignment_executor is required to execute assignments")

        results = [
            self.assignment_executor.execute(assignment)
            for assignment in ordered
        ]

        return self.collect_results(results)

    def collect_results(self, results: list) -> list:
        """
        Return a defensive copy of collected execution results.
        """
        return list(results)

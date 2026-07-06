from __future__ import annotations

from typing import Any

from .employee_supervisor import (
    EmployeeSupervisorReview,
    SupervisorDecision,
)


class EmployeeSupervisorStore:
    def __init__(self) -> None:
        self._reviews: dict[str, EmployeeSupervisorReview] = {}
        self._employee_index: dict[str, list[str]] = {}

    def review(
        self,
        employee_id: str,
        supervisor_id: str,
        decision: SupervisorDecision | str,
        comments: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> EmployeeSupervisorReview:

        review = EmployeeSupervisorReview(
            employee_id=employee_id,
            supervisor_id=supervisor_id,
            decision=decision,
            comments=comments,
            metadata=metadata or {},
        )

        self._reviews[review.review_id] = review
        self._employee_index.setdefault(employee_id, []).append(
            review.review_id
        )

        return review

    def get(self, review_id: str):
        return self._reviews.get(review_id)

    def list(self, employee_id: str):
        return [
            self._reviews[rid]
            for rid in self._employee_index.get(employee_id, [])
        ]

    def latest(self, employee_id: str):
        reviews = self.list(employee_id)
        return reviews[-1] if reviews else None

    def count(self, employee_id: str | None = None):
        if employee_id is None:
            return len(self._reviews)

        return len(self.list(employee_id))

    def snapshot(self):
        return {
            rid: review.snapshot()
            for rid, review in self._reviews.items()
        }

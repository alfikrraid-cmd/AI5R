"""
it_department_operating_model.py (implements ITD-001) --
ITDepartmentOperatingModel, the IT Department's operational workflow.

Sequences six stages -- Sprint Planning, Work (MWO) Assignment,
Engineering Queue, Progress Tracking, Review, Release -- purely by
delegating to already-canonical WORKFORCE components:

    Sprint Planning     -> Department.start_sprint()
    Work (MWO) Assignment -> ProjectManagerCapability.breakdown_sprint()/.assign_tasks()
    Engineering Queue   -> WorkBoard.publish()/.claim()
    Progress Tracking   -> EmployeeRuntime.run() / WorkBoard.complete()
    Review Workflow     -> EmployeeRuntime.review() / ApprovalChainRuntime
    Release Workflow    -> WorkBoard.release()

No new state machine, registry, or runtime is introduced. Organization
and Department come from the caller (e.g. ITDepartmentPack); this class
never constructs an Organization/Department itself. ApprovalChainRuntime
requires ReportingRuntime/PositionRuntime wiring that is the caller's
own responsibility (per its own module docstring) -- it is accepted
here only as an already-constructed, optional dependency, never built
internally.
"""

from __future__ import annotations

from typing import Any

from WORKFORCE.approval_chain_runtime import ApprovalChainRuntime
from WORKFORCE.department import Department
from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.employee_runtime import EmployeeRuntime, RuntimeResult
from WORKFORCE.project_manager_capability import ProjectManagerCapability
from WORKFORCE.sprint import Sprint
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.work_item import WorkItem


class ITDepartmentOperatingModel:
    def __init__(
        self,
        project_manager_capability: ProjectManagerCapability | None = None,
        employee_runtime: EmployeeRuntime | None = None,
        work_board: WorkBoard | None = None,
        approval_chain_runtime: ApprovalChainRuntime | None = None,
    ) -> None:
        self.project_manager_capability = project_manager_capability or ProjectManagerCapability()
        self.employee_runtime = employee_runtime or EmployeeRuntime()
        self.work_board = work_board or WorkBoard()
        self.approval_chain_runtime = approval_chain_runtime

    # ------------------------------------------------------------------
    # 1. Sprint Planning
    # ------------------------------------------------------------------

    def plan_sprint(self, department: Department, objective: str) -> Sprint:
        return department.start_sprint(objective=objective)["sprint"]

    # ------------------------------------------------------------------
    # 2. Work (MWO) Assignment
    # ------------------------------------------------------------------

    def break_down_and_assign(
        self,
        project_manager: DigitalEmployee,
        sprint: Sprint,
        employees: list[DigitalEmployee],
    ) -> dict[str, Any]:
        breakdown = self.project_manager_capability.breakdown_sprint(project_manager, sprint)
        assignment = self.project_manager_capability.assign_tasks(
            project_manager, breakdown["tasks"], employees
        )
        return {"tasks": breakdown["tasks"], "assignments": assignment["assignments"]}

    # ------------------------------------------------------------------
    # 3. Engineering Queue
    # ------------------------------------------------------------------

    def enqueue(self, work_item: WorkItem) -> WorkItem:
        return self.work_board.publish(work_item)

    def claim(self, employee: DigitalEmployee, work_item_id: str) -> WorkItem:
        return self.work_board.claim(employee, work_item_id)

    # ------------------------------------------------------------------
    # 4. Progress Tracking
    # ------------------------------------------------------------------

    def track_progress(self, employee: DigitalEmployee, work_item: WorkItem) -> list[RuntimeResult]:
        return self.employee_runtime.run(employee, work_item)

    def complete(self, employee: DigitalEmployee, work_item_id: str) -> WorkItem:
        return self.work_board.complete(employee, work_item_id)

    # ------------------------------------------------------------------
    # 5. Review Workflow
    # ------------------------------------------------------------------

    def review(self, employee: DigitalEmployee, work_item: WorkItem) -> RuntimeResult:
        return self.employee_runtime.review(employee, work_item)

    def approve(self, request_amount: float, employee_id: str, decision: Any) -> Any:
        if self.approval_chain_runtime is None:
            raise ValueError(
                "ApprovalChainRuntime was not configured for this operating model"
            )

        approver = self.approval_chain_runtime.resolve_approver(request_amount)
        if approver is None:
            raise ValueError("No approver available for this request")

        return self.approval_chain_runtime.record_decision(
            employee_id=employee_id,
            supervisor_id=approver.employee_id,
            decision=decision,
        )

    # ------------------------------------------------------------------
    # 6. Release Workflow
    # ------------------------------------------------------------------

    def release(self, work_item_id: str) -> WorkItem:
        return self.work_board.release(work_item_id)

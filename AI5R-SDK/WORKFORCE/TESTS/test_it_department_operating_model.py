"""ITDepartmentOperatingModel tests -- ITD-001.

The operating model sequences six stages (Sprint Planning, Work/MWO
Assignment, Engineering Queue, Progress Tracking, Review, Release)
purely by delegating to already-canonical WORKFORCE components
(ITDepartmentPack, ProjectManagerCapability, WorkBoard, EmployeeRuntime,
ApprovalChainRuntime). It introduces no new state machine, registry, or
runtime of its own.
"""

from unittest.mock import MagicMock

from WORKFORCE.approval_chain_runtime import ApprovalChainRuntime
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.it_department_operating_model import ITDepartmentOperatingModel
from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.organization_factory import OrganizationFactory
from WORKFORCE.project_manager_capability import ProjectManagerCapability
from WORKFORCE.work_board import WorkBoard


def _it_department():
    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    pack = ITDepartmentPack().manufacture(organization)
    department = pack["department"]
    employees = pack["employees"]

    project_manager = [e for e in employees if e.position_id == "PROJECT_MANAGER"][0]
    backend_engineer = [e for e in employees if e.position_id == "BACKEND_ENGINEER"][0]

    return department, employees, project_manager, backend_engineer


# ---------------------------------------------------------------------------
# End-to-end pipeline -- reuses real components throughout
# ---------------------------------------------------------------------------


def test_full_pipeline_sprint_to_release():
    department, employees, project_manager, backend_engineer = _it_department()
    model = ITDepartmentOperatingModel()

    # 1. Sprint Planning
    sprint = model.plan_sprint(department, objective="Build Login API")
    assert sprint.sprint_id in department.sprint_ids

    # 2. Work (MWO) Assignment
    result = model.break_down_and_assign(project_manager, sprint, employees)
    assert len(result["tasks"]) == 6
    backend_task = [t for t in result["tasks"] if t.assigned_position_id == "BACKEND_ENGINEER"][0]
    assert backend_task.assigned_employee_id == backend_engineer.employee_id

    # 3. Engineering Queue
    model.enqueue(backend_task)
    assert backend_task in model.work_board.available_work_items()

    claimed = model.claim(backend_engineer, backend_task.work_item_id)
    assert claimed.status == "CLAIMED"

    # 4. Progress Tracking
    results = model.track_progress(backend_engineer, claimed)
    assert [r.phase for r in results[1:]] == ["EXECUTING", "REVIEWING", "LEARNING", "IDLE"]

    completed = model.complete(backend_engineer, claimed.work_item_id)
    assert completed.status == "COMPLETED"

    # 5. Review Workflow
    review_result = model.review(backend_engineer, completed)
    assert review_result.phase == "LEARNING"

    # 6. Release Workflow
    released = model.release(completed.work_item_id)
    assert released.status == "RELEASED"
    assert released in model.work_board.released_work_items()


# ---------------------------------------------------------------------------
# Pure delegation -- no independent logic
# ---------------------------------------------------------------------------


def test_plan_sprint_delegates_to_department_start_sprint():
    department = MagicMock()
    department.start_sprint.return_value = {"sprint": "SPRINT-STUB"}
    model = ITDepartmentOperatingModel()

    result = model.plan_sprint(department, objective="Build Login API")

    department.start_sprint.assert_called_once_with(objective="Build Login API")
    assert result == "SPRINT-STUB"


def test_enqueue_delegates_to_work_board_publish():
    work_board = MagicMock(spec=WorkBoard)
    work_board.publish.return_value = "PUBLISHED-STUB"
    model = ITDepartmentOperatingModel(work_board=work_board)

    result = model.enqueue("WORK-ITEM-STUB")

    work_board.publish.assert_called_once_with("WORK-ITEM-STUB")
    assert result == "PUBLISHED-STUB"


def test_claim_delegates_to_work_board_claim():
    work_board = MagicMock(spec=WorkBoard)
    work_board.claim.return_value = "CLAIMED-STUB"
    model = ITDepartmentOperatingModel(work_board=work_board)

    result = model.claim("EMPLOYEE-STUB", "WORK-1")

    work_board.claim.assert_called_once_with("EMPLOYEE-STUB", "WORK-1")
    assert result == "CLAIMED-STUB"


def test_complete_delegates_to_work_board_complete():
    work_board = MagicMock(spec=WorkBoard)
    work_board.complete.return_value = "COMPLETED-STUB"
    model = ITDepartmentOperatingModel(work_board=work_board)

    result = model.complete("EMPLOYEE-STUB", "WORK-1")

    work_board.complete.assert_called_once_with("EMPLOYEE-STUB", "WORK-1")
    assert result == "COMPLETED-STUB"


def test_release_delegates_to_work_board_release():
    work_board = MagicMock(spec=WorkBoard)
    work_board.release.return_value = "RELEASED-STUB"
    model = ITDepartmentOperatingModel(work_board=work_board)

    result = model.release("WORK-1")

    work_board.release.assert_called_once_with("WORK-1")
    assert result == "RELEASED-STUB"


def test_review_delegates_to_employee_runtime_review():
    employee_runtime = MagicMock(spec=EmployeeRuntime)
    employee_runtime.review.return_value = "REVIEW-STUB"
    model = ITDepartmentOperatingModel(employee_runtime=employee_runtime)

    result = model.review("EMPLOYEE-STUB", "WORK-ITEM-STUB")

    employee_runtime.review.assert_called_once_with("EMPLOYEE-STUB", "WORK-ITEM-STUB")
    assert result == "REVIEW-STUB"


def test_track_progress_delegates_to_employee_runtime_run():
    employee_runtime = MagicMock(spec=EmployeeRuntime)
    employee_runtime.run.return_value = ["RESULT-STUB"]
    model = ITDepartmentOperatingModel(employee_runtime=employee_runtime)

    result = model.track_progress("EMPLOYEE-STUB", "WORK-ITEM-STUB")

    employee_runtime.run.assert_called_once_with("EMPLOYEE-STUB", "WORK-ITEM-STUB")
    assert result == ["RESULT-STUB"]


def test_break_down_and_assign_delegates_to_project_manager_capability():
    pm_capability = MagicMock(spec=ProjectManagerCapability)
    pm_capability.breakdown_sprint.return_value = {"tasks": ["TASK-STUB"]}
    pm_capability.assign_tasks.return_value = {"assignments": ["ASSIGNMENT-STUB"]}
    model = ITDepartmentOperatingModel(project_manager_capability=pm_capability)

    result = model.break_down_and_assign("PM-STUB", "SPRINT-STUB", ["EMP-STUB"])

    pm_capability.breakdown_sprint.assert_called_once_with("PM-STUB", "SPRINT-STUB")
    pm_capability.assign_tasks.assert_called_once_with("PM-STUB", ["TASK-STUB"], ["EMP-STUB"])
    assert result == {"tasks": ["TASK-STUB"], "assignments": ["ASSIGNMENT-STUB"]}


# ---------------------------------------------------------------------------
# Approval Chain composition -- optional, caller-supplied, never constructed internally
# ---------------------------------------------------------------------------


def test_approve_raises_when_no_approval_chain_runtime_configured():
    model = ITDepartmentOperatingModel()

    try:
        model.approve(request_amount=100.0, employee_id="EMP-1", decision="APPROVED")
        assert False, "expected ValueError when no ApprovalChainRuntime is configured"
    except ValueError as exc:
        assert "ApprovalChainRuntime" in str(exc)


def test_approve_delegates_to_approval_chain_runtime():
    approval_chain_runtime = MagicMock(spec=ApprovalChainRuntime)
    approver = MagicMock()
    approver.employee_id = "EMP-MANAGER"
    approval_chain_runtime.resolve_approver.return_value = approver
    approval_chain_runtime.record_decision.return_value = "REVIEW-STUB"

    model = ITDepartmentOperatingModel(approval_chain_runtime=approval_chain_runtime)

    result = model.approve(request_amount=500.0, employee_id="EMP-1", decision="APPROVED")

    approval_chain_runtime.resolve_approver.assert_called_once_with(500.0)
    approval_chain_runtime.record_decision.assert_called_once_with(
        employee_id="EMP-1",
        supervisor_id="EMP-MANAGER",
        decision="APPROVED",
    )
    assert result == "REVIEW-STUB"


def test_approve_raises_when_no_approver_available():
    approval_chain_runtime = MagicMock(spec=ApprovalChainRuntime)
    approval_chain_runtime.resolve_approver.return_value = None
    model = ITDepartmentOperatingModel(approval_chain_runtime=approval_chain_runtime)

    try:
        model.approve(request_amount=500.0, employee_id="EMP-1", decision="APPROVED")
        assert False, "expected ValueError when no approver is available"
    except ValueError as exc:
        assert "No approver available" in str(exc)


# ---------------------------------------------------------------------------
# Structural verification -- no new foundation, no duplicate runtime
# ---------------------------------------------------------------------------


def test_operating_model_holds_only_its_four_dependencies():
    model = ITDepartmentOperatingModel()

    attributes = vars(model)

    assert len(attributes) == 4
    assert set(attributes.keys()) == {
        "project_manager_capability",
        "employee_runtime",
        "work_board",
        "approval_chain_runtime",
    }

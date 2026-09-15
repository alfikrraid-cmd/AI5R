from __future__ import annotations

import pytest

from WORKFORCE import (
    ApprovalChainRuntime,
    Approver,
    ChiefApprovalRecord,
    ChiefApprovalRequiredError,
    DigitalEmployeeFactory,
    ITDepartmentPack,
    OrganizationFactory,
    WorkBoard,
)
from WORKFORCE.work_item import WorkItem
from WORKFORCE.it_department_operating_model import ITDepartmentOperatingModel
from WORKFORCE.approval_chain_runtime import (
    is_production_work_item,
    validate_chief_approval,
)


def _claimed_item(board: WorkBoard, is_production: bool = False) -> tuple[any, WorkItem]:
    metadata = {}
    if is_production:
        metadata["is_production"] = True

    item = WorkItem(
        title="Deploy to production cluster",
        assigned_position_id="BACKEND_ENGINEER",
        metadata=metadata,
    )

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-TEST",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    board.publish(item)
    board.claim(employee, item.work_item_id)

    return employee, item


# ---------------------------------------------------------------------------
# 1. Approval runtime imports successfully
# ---------------------------------------------------------------------------


def test_approval_runtime_imports_successfully():
    from WORKFORCE.approval_chain_runtime import (
        ApprovalChainRuntime as ImportedRuntime,
    )
    from WORKFORCE.approval_chain_runtime import (
        ChiefApprovalRecord as ImportedRecord,
    )
    from WORKFORCE.approval_chain_runtime import (
        ChiefApprovalRequiredError as ImportedError,
    )

    runtime = ImportedRuntime()
    assert runtime is not None
    assert runtime.resolve_approver(500.0) is not None
    assert runtime.resolve_approver(500.0).employee_id == "ID-PROJECT_MANAGER"
    assert runtime.resolve_approver(5000.0).employee_id == "ID-CTO"
    assert runtime.resolve_approver(50000.0).employee_id == "raid"
    assert runtime.resolve_approver(50000.0).is_human is True


# ---------------------------------------------------------------------------
# 2. Pending approval
# ---------------------------------------------------------------------------


def test_pending_approval_blocks_production_release():
    runtime = ApprovalChainRuntime()
    board = WorkBoard(approval_chain_runtime=runtime)
    employee, item = _claimed_item(board, is_production=True)
    board.complete(employee, item.work_item_id)

    pending = runtime.request_chief_approval(
        work_item_id=item.work_item_id,
        requester_id="EMP-AI-1",
    )

    assert pending.status == "PENDING"
    assert pending.work_item_id == item.work_item_id

    # Releasing with pending approval must fail closed
    with pytest.raises(ChiefApprovalRequiredError) as exc:
        board.release(item.work_item_id, approval=pending)

    assert "PENDING" in str(exc.value)
    assert item in board.completed_work_items()
    assert board.released_work_items() == []


# ---------------------------------------------------------------------------
# 3. Explicit Chief approval
# ---------------------------------------------------------------------------


def test_explicit_chief_approval_allows_production_release():
    runtime = ApprovalChainRuntime()
    board = WorkBoard(approval_chain_runtime=runtime)
    employee, item = _claimed_item(board, is_production=True)
    board.complete(employee, item.work_item_id)

    approval = runtime.grant_chief_approval(
        work_item_id=item.work_item_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
    )

    assert approval.status == "APPROVED"
    assert approval.is_human is True
    assert approval.approver_role == "CHIEF_ARCHITECT"

    released = board.release(item.work_item_id, approval=approval)

    assert released.status == "RELEASED"
    assert released in board.released_work_items()
    assert board.completed_work_items() == []
    assert "chief_approval" in released.metadata
    assert released.metadata["chief_approval"]["approver_id"] == "raid"


# ---------------------------------------------------------------------------
# 4. Rejection
# ---------------------------------------------------------------------------


def test_chief_rejection_blocks_production_release():
    runtime = ApprovalChainRuntime()
    board = WorkBoard(approval_chain_runtime=runtime)
    employee, item = _claimed_item(board, is_production=True)
    board.complete(employee, item.work_item_id)

    rejection = runtime.reject_chief_approval(
        work_item_id=item.work_item_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
        reason="Security posture verification failed",
    )

    assert rejection.status == "REJECTED"

    with pytest.raises(ChiefApprovalRequiredError) as exc:
        board.release(item.work_item_id, approval=rejection)

    assert "REJECTED" in str(exc.value)
    assert item in board.completed_work_items()
    assert board.released_work_items() == []


# ---------------------------------------------------------------------------
# 5. Wrong / non-Chief approver denied (AI roles, self-approval, magic string)
# ---------------------------------------------------------------------------


def test_ai_employee_cannot_self_approve_production_release():
    board = WorkBoard()
    employee, item = _claimed_item(board, is_production=True)
    board.complete(employee, item.work_item_id)

    # 5a. AI CTO trying to approve
    ai_cto_approval = ChiefApprovalRecord(
        work_item_id=item.work_item_id,
        approver_id="ID-CTO",
        approver_role="CTO",
        is_human=False,
        status="APPROVED",
    )
    with pytest.raises(ChiefApprovalRequiredError) as exc:
        board.release(item.work_item_id, approval=ai_cto_approval)
    assert "AI employee" in str(exc.value) or "not marked as human" in str(exc.value)

    # 5b. AI QA trying to approve
    ai_qa_approval = ChiefApprovalRecord(
        work_item_id=item.work_item_id,
        approver_id="ID-QA_ENGINEER",
        approver_role="QA_ENGINEER",
        is_human=False,
        status="APPROVED",
    )
    with pytest.raises(ChiefApprovalRequiredError) as exc:
        board.release(item.work_item_id, approval=ai_qa_approval)
    assert "AI employee" in str(exc.value) or "not marked as human" in str(exc.value)

    # 5c. AI employee impersonating Chief role but with is_human=False
    fake_chief_approval = ChiefApprovalRecord(
        work_item_id=item.work_item_id,
        approver_id="AI-AGENT-001",
        approver_role="CHIEF_ARCHITECT",
        is_human=False,
        status="APPROVED",
    )
    with pytest.raises(ChiefApprovalRequiredError) as exc:
        board.release(item.work_item_id, approval=fake_chief_approval)
    assert "AI employee" in str(exc.value) or "not marked as human" in str(exc.value)

    # 5d. Non-Chief human role (e.g. human developer without Chief authority)
    human_dev_approval = ChiefApprovalRecord(
        work_item_id=item.work_item_id,
        approver_id="dev-123",
        approver_role="BACKEND_ENGINEER",
        is_human=True,
        status="APPROVED",
    )
    with pytest.raises(ChiefApprovalRequiredError) as exc:
        board.release(item.work_item_id, approval=human_dev_approval)
    assert "lacks Chief release authority" in str(exc.value)

    # 5e. Magic string "CHIEF_APPROVED" must be rejected
    with pytest.raises(ChiefApprovalRequiredError) as exc:
        board.release(item.work_item_id, approval="CHIEF_APPROVED")
    assert "Unstructured string approval" in str(exc.value) or "INVALID" in str(exc.value)


# ---------------------------------------------------------------------------
# 6. Production release without approval blocked
# ---------------------------------------------------------------------------


def test_production_release_without_approval_blocked():
    board = WorkBoard()
    employee, item = _claimed_item(board, is_production=True)
    board.complete(employee, item.work_item_id)

    with pytest.raises(ChiefApprovalRequiredError) as exc:
        board.release(item.work_item_id)

    assert "Human Chief approval is MISSING" in str(exc.value)
    assert board.completed_work_items() == [item]
    assert board.released_work_items() == []


def test_environment_production_flag_triggers_chief_gate():
    board = WorkBoard()
    item = WorkItem(
        title="Deploy to prod",
        assigned_position_id="BACKEND_ENGINEER",
        metadata={"environment": "production"},
    )
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-ENV-TEST",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    assert is_production_work_item(item) is True
    board.publish(item)
    board.claim(employee, item.work_item_id)
    board.complete(employee, item.work_item_id)

    with pytest.raises(ChiefApprovalRequiredError):
        board.release(item.work_item_id)


# ---------------------------------------------------------------------------
# 7. Production release with valid Chief approval allowed via WorkBoard runtime
# ---------------------------------------------------------------------------


def test_production_release_resolves_approval_from_runtime():
    runtime = ApprovalChainRuntime()
    board = WorkBoard(approval_chain_runtime=runtime)
    employee, item = _claimed_item(board, is_production=True)
    board.complete(employee, item.work_item_id)

    # Grant approval in runtime ahead of release call
    runtime.grant_chief_approval(
        work_item_id=item.work_item_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
    )

    # Releasing without explicit arg resolves from runtime automatically
    released = board.release(item.work_item_id)
    assert released.status == "RELEASED"
    assert released in board.released_work_items()


# ---------------------------------------------------------------------------
# 8. Non-production lifecycle regression
# ---------------------------------------------------------------------------


def test_non_production_work_item_releases_without_approval():
    board = WorkBoard()
    employee, item = _claimed_item(board, is_production=False)
    assert is_production_work_item(item) is False

    board.complete(employee, item.work_item_id)
    released = board.release(item.work_item_id)

    assert released.status == "RELEASED"
    assert board.released_work_items() == [released]
    assert board.completed_work_items() == []


def test_staging_environment_releases_without_chief_approval():
    board = WorkBoard()
    item = WorkItem(
        title="Deploy to staging",
        assigned_position_id="BACKEND_ENGINEER",
        metadata={"environment": "staging"},
    )
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-STAGING-TEST",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    assert is_production_work_item(item) is False
    board.publish(item)
    board.claim(employee, item.work_item_id)
    board.complete(employee, item.work_item_id)

    released = board.release(item.work_item_id)
    assert released.status == "RELEASED"


# ---------------------------------------------------------------------------
# 9. ITDepartmentOperatingModel integration with Chief Approval Gate
# ---------------------------------------------------------------------------


def test_operating_model_production_gate_integration():
    organization = OrganizationFactory().manufacture("AI5R")["asset"]
    pack = ITDepartmentPack().manufacture(organization)
    employees = pack["employees"]
    backend = [e for e in employees if e.position_id == "BACKEND_ENGINEER"][0]

    approval_runtime = ApprovalChainRuntime()
    model = ITDepartmentOperatingModel(approval_chain_runtime=approval_runtime)

    prod_item = WorkItem(
        title="Production Hotfix",
        assigned_position_id="BACKEND_ENGINEER",
        metadata={"is_production": True},
    )

    model.enqueue(prod_item)
    model.claim(backend, prod_item.work_item_id)
    model.track_progress(backend, prod_item)
    model.complete(backend, prod_item.work_item_id)
    model.review(backend, prod_item)

    # 1. Attempting release without Chief approval fails closed
    with pytest.raises(ChiefApprovalRequiredError):
        model.release(prod_item.work_item_id)

    # 2. Granting Chief approval allows release
    approval_runtime.grant_chief_approval(
        work_item_id=prod_item.work_item_id,
        approver_id="raid",
        approver_role="CHIEF_ARCHITECT",
        is_human=True,
    )

    released = model.release(prod_item.work_item_id)
    assert released.status == "RELEASED"
    assert released in model.work_board.released_work_items()

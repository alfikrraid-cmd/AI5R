from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.work_item import WorkItem


def test_employee_can_claim_matching_work_item():
    board = WorkBoard()

    item = WorkItem(
        title="Implement backend API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-001",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["API"],
    )["employee"]

    board.publish(item)
    claimed = board.claim(employee, item.work_item_id)

    assert claimed.status == "CLAIMED"
    assert claimed.assigned_employee_id == employee.employee_id
    assert board.available_work_items() == []
    assert board.claimed_work_items() == [claimed]


def test_inactive_employee_cannot_claim_work_item():
    board = WorkBoard()

    item = WorkItem(
        title="Implement backend API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-002",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    employee.status = "INACTIVE"

    board.publish(item)

    try:
        board.claim(employee, item.work_item_id)
    except ValueError as exc:
        assert "Only ACTIVE employee" in str(exc)
    else:
        raise AssertionError("Expected inactive employee claim to fail")


def test_wrong_position_employee_cannot_claim_work_item():
    board = WorkBoard()

    item = WorkItem(
        title="Implement backend API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI QA Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-QA-001",
        position_id="QA_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    board.publish(item)

    try:
        board.claim(employee, item.work_item_id)
    except ValueError as exc:
        assert "position does not match" in str(exc)
    else:
        raise AssertionError("Expected wrong-position claim to fail")


def test_unpublished_work_item_cannot_be_claimed():
    board = WorkBoard()

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-003",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    try:
        board.claim(employee, "WORK-MISSING")
    except ValueError as exc:
        assert "not available" in str(exc)
    else:
        raise AssertionError("Expected missing work item claim to fail")

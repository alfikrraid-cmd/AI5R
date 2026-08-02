from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.work_item import WorkItem


def _claimed_item(board: WorkBoard):
    item = WorkItem(
        title="Implement backend API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-COMPLETE",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    board.publish(item)
    board.claim(employee, item.work_item_id)

    return employee, item


def test_claiming_employee_can_complete_work_item():
    board = WorkBoard()
    employee, item = _claimed_item(board)

    completed = board.complete(employee, item.work_item_id)

    assert completed.status == "COMPLETED"
    assert board.claimed_work_items() == []
    assert board.completed_work_items() == [completed]


def test_other_employee_cannot_complete_work_item():
    board = WorkBoard()
    _, item = _claimed_item(board)

    other = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer 2",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-OTHER",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    try:
        board.complete(other, item.work_item_id)
    except ValueError as exc:
        assert "claimed the work item" in str(exc)
    else:
        raise AssertionError("Expected non-claiming employee complete to fail")


def test_unclaimed_work_item_cannot_be_completed():
    board = WorkBoard()
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-004",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    try:
        board.complete(employee, "WORK-MISSING")
    except ValueError as exc:
        assert "not claimed" in str(exc)
    else:
        raise AssertionError("Expected missing/unclaimed work item complete to fail")


def test_completed_work_item_can_be_released():
    board = WorkBoard()
    employee, item = _claimed_item(board)
    board.complete(employee, item.work_item_id)

    released = board.release(item.work_item_id)

    assert released.status == "RELEASED"
    assert board.completed_work_items() == []
    assert board.released_work_items() == [released]


def test_unclaimed_work_item_cannot_be_released():
    board = WorkBoard()

    try:
        board.release("WORK-MISSING")
    except ValueError as exc:
        assert "COMPLETED" in str(exc)
    else:
        raise AssertionError("Expected release of a non-completed work item to fail")


def test_released_work_items_empty_initially():
    board = WorkBoard()
    assert board.released_work_items() == []

from WORKFORCE.work_board import WorkBoard
from WORKFORCE.work_item import WorkItem


def test_publish_work_item():

    board = WorkBoard()

    item = WorkItem(
        title="Backend API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    board.publish(item)

    assert item.status == "PUBLISHED"

    assert len(
        board.available_work_items()
    ) == 1


def test_multiple_work_items():

    board = WorkBoard()

    for i in range(5):

        board.publish(
            WorkItem(
                title=f"Task {i}",
                assigned_position_id="BACKEND_ENGINEER",
            )
        )

    assert len(
        board.available_work_items()
    ) == 5


def test_claimed_and_completed_empty_initially():

    board = WorkBoard()

    assert board.claimed_work_items() == []

    assert board.completed_work_items() == []

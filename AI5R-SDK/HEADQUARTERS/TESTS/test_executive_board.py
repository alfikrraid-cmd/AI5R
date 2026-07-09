from HEADQUARTERS import (
    Executive,
    ExecutiveBoard,
)


def test_board_registration():

    board = ExecutiveBoard()

    raid = Executive(

        executive_id="CEO",

        name="Raid",

        title="Chief Executive Officer",

        department="Executive",

    )

    board.register(raid)

    assert len(board.all()) == 1

    assert board.get("CEO").name == "Raid"


def test_assign_mission():

    raid = Executive(

        executive_id="CEO",

        name="Raid",

        title="Chief Executive Officer",

        department="Executive",

    )

    result = raid.assign_mission(

        "Build ERP"

    )

    assert result["status"] == "WORKING"

    raid.complete()

    assert raid.status == "READY"


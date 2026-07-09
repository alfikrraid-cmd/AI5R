from HEADQUARTERS import ExecutiveBoardFactory


def test_executive_board_factory_creates_full_board():
    board = ExecutiveBoardFactory().create()

    assert len(board.all()) == 8
    assert board.get("CEO").name == "Raid"
    assert board.get("CTO").name == "Jazari"
    assert board.get("CFO").name == "Graham"
    assert board.get("CLO").name == "Hakim"
    assert board.get("CKO").name == "Sofia"


def test_executives_have_responsibilities_and_motto():
    board = ExecutiveBoardFactory().create()

    jazari = board.get("CTO")
    graham = board.get("CFO")

    assert "Architecture" in jazari.responsibilities
    assert jazari.motto == "Think before coding."
    assert "ROI" in graham.responsibilities
    assert "financial consequence" in graham.motto

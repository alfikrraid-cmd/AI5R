from HEADQUARTERS import (
    Executive,
    ExecutiveBoard,
    ExecutiveMeetingRuntime,
)


def _board():
    board = ExecutiveBoard()

    executives = [
        ("CEO", "Raid", "Chief Executive Officer", "Executive"),
        ("CTO", "Jazari", "Chief Technology Officer", "Technology"),
        ("CFO", "Graham", "Chief Financial Officer", "Finance"),
        ("CLO", "Hakim", "Chief Legal Officer", "Legal"),
        ("COO", "Orion", "Chief Operating Officer", "Operations"),
        ("CMO", "Nova", "Chief Marketing Officer", "Marketing"),
        ("CHRO", "Hadi", "Chief Human Resources Officer", "Workforce"),
        ("CKO", "Sofia", "Chief Knowledge Officer", "Knowledge"),
    ]

    for executive_id, name, title, department in executives:
        board.register(
            Executive(
                executive_id=executive_id,
                name=name,
                title=title,
                department=department,
            )
        )

    return board


def test_executive_meeting_collects_opinions():
    meeting = ExecutiveMeetingRuntime(_board()).run(
        mission="Build Restaurant Management System"
    )

    assert meeting.status == "EXECUTIVE_RECOMMENDATION_READY"
    assert meeting.leader == "Raid"
    assert len(meeting.opinions) == 8
    assert meeting.opinions[0].executive_name == "Raid"
    assert meeting.opinions[1].executive_name == "Jazari"
    assert "approving" in meeting.final_recommendation


def test_executive_meeting_snapshot_is_dashboard_ready():
    meeting = ExecutiveMeetingRuntime(_board()).run(
        mission="Build Login API",
        participants=["CEO", "CTO", "CFO"],
    )

    snapshot = meeting.snapshot()

    assert snapshot["meeting_id"].startswith("MEET-")
    assert snapshot["mission"] == "Build Login API"
    assert len(snapshot["opinions"]) == 3
    assert snapshot["opinions"][1]["perspective"] == "Technology and architecture"
    assert snapshot["status"] == "EXECUTIVE_RECOMMENDATION_READY"

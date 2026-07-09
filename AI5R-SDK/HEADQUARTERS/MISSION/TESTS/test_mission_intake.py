from HEADQUARTERS.MISSION import (
    MissionIntakeEngine,
    MissionRegistry,
)


def test_mission_intake_creates_mission_object():
    mission = MissionIntakeEngine().create(
        title="Build Restaurant ERP",
        description="Create MVP for restaurant operations",
        requester="Chief",
        priority="HIGH",
    )

    assert mission.mission_id.startswith("MISSION-")
    assert mission.title == "Build Restaurant ERP"
    assert mission.status == "INTAKE"
    assert mission.priority == "HIGH"
    assert mission.requester == "Chief"


def test_mission_rejects_empty_title():
    try:
        MissionIntakeEngine().create(title="   ")
    except ValueError as exc:
        assert "Mission title is required" in str(exc)
    else:
        raise AssertionError("Expected empty mission title to fail")


def test_mission_lifecycle():
    mission = MissionIntakeEngine().create(
        title="Build Login API",
    )

    mission.assign_executive_review(
        leader="Raid",
        participants=["Jazari", "Graham", "Hakim"],
    )

    assert mission.status == "EXECUTIVE_REVIEW"
    assert mission.leader == "Raid"
    assert mission.participants == ["Jazari", "Graham", "Hakim"]

    mission.approve("Approved for MVP manufacturing")
    assert mission.status == "APPROVED"
    assert mission.recommendation == "Approved for MVP manufacturing"

    mission.start_manufacturing()
    assert mission.status == "MANUFACTURING"

    mission.deliver()
    assert mission.status == "DELIVERED"


def test_mission_registry_tracks_missions():
    registry = MissionRegistry()
    mission = MissionIntakeEngine().create(title="Build CRM")

    registry.register(mission)

    assert registry.get(mission.mission_id) == mission
    assert registry.snapshot()[0]["title"] == "Build CRM"

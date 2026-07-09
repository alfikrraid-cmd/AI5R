from DEMOS.DEMO_001.login_api_demo import run_demo
from MISSION_CONTROL.api import MissionControlAPI


def test_mission_control_api_builds_dashboard_snapshot_from_demo():
    demo_result = run_demo()

    snapshot = MissionControlAPI().snapshot_from_demo_result(demo_result)

    assert snapshot["status"] == "MISSION_CONTROL_READY"
    assert snapshot["mission"]["name"] == "Build FastAPI Login API"
    assert len(snapshot["organization"]) >= 1
    assert len(snapshot["timeline"]) == len(demo_result["activity_stream"])
    assert snapshot["statistics"]["planned_artifacts"] == 10
    assert snapshot["statistics"]["employees_active"] >= 1


def test_mission_control_api_exposes_digital_twins():
    demo_result = run_demo()

    snapshot = MissionControlAPI().snapshot_from_demo_result(demo_result)

    assert snapshot["digital_twins"]
    first_twin = list(snapshot["digital_twins"].values())[0]

    assert first_twin["entity_type"] == "DIGITAL_EMPLOYEE"
    assert first_twin["status"] == "COMPLETED"

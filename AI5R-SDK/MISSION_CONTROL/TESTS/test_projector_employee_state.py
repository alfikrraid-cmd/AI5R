from MISSION_CONTROL.projector import MissionControlProjector


def test_employee_activity_updates_same_employee_state_without_duplication():
    projector = MissionControlProjector()

    projector.project(
        {
            "event_type": "EMPLOYEE_ACTIVITY_RECORDED",
            "payload": {
                "employee_id": "EMP-001",
                "status": "THINKING",
                "progress": 40,
                "activity_type": "THINKING",
            },
        }
    )

    projector.project(
        {
            "event_type": "EMPLOYEE_ACTIVITY_RECORDED",
            "payload": {
                "employee_id": "EMP-001",
                "status": "EXECUTING",
                "progress": 70,
                "activity_type": "EXECUTING",
            },
        }
    )

    snapshot = projector.model.snapshot()

    assert len(snapshot["organization"]) == 1
    assert snapshot["organization"][0]["employee_id"] == "EMP-001"
    assert snapshot["organization"][0]["status"] == "EXECUTING"
    assert snapshot["organization"][0]["progress"] == 70
    assert len(snapshot["timeline"]) == 2


def test_multiple_employees_are_tracked_separately():
    projector = MissionControlProjector()

    for employee_id in ["EMP-001", "EMP-002"]:
        projector.project(
            {
                "event_type": "EMPLOYEE_ACTIVITY_RECORDED",
                "payload": {
                    "employee_id": employee_id,
                    "status": "THINKING",
                    "progress": 30,
                    "activity_type": "THINKING",
                },
            }
        )

    snapshot = projector.model.snapshot()

    assert len(snapshot["organization"]) == 2
    assert len(snapshot["timeline"]) == 2

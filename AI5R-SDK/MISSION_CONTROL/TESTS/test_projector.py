from MISSION_CONTROL.projector import MissionControlProjector


def test_employee_activity_updates_read_model():

    projector = MissionControlProjector()

    projector.project({

        "event_type":"EMPLOYEE_ACTIVITY_RECORDED",

        "payload":{

            "employee_id":"EMP-001",

            "status":"THINKING",

            "progress":40,

            "activity_type":"THINKING"

        }

    })

    snapshot = projector.model.snapshot()

    assert len(snapshot["organization"]) == 1

    assert snapshot["organization"][0]["status"] == "THINKING"

    assert len(snapshot["timeline"]) == 1

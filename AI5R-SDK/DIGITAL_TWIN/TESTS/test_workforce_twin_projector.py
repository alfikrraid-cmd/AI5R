from DIGITAL_TWIN.workforce_twin_projector import WorkforceTwinProjector


def test_workforce_activity_event_updates_employee_twin():
    projector = WorkforceTwinProjector()

    projector.project(
        {
            "event_type": "EMPLOYEE_ACTIVITY_RECORDED",
            "payload": {
                "employee_id": "EMP-001",
                "activity_type": "THINKING",
                "status": "CAPABILITY_SELECTED",
                "message": "Employee selected capabilities",
                "progress": 35,
                "work_item_id": "WORK-001",
                "sprint_id": "SPRINT-001",
                "mission_id": "MISSION-001",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "metadata": {"selected_capabilities": ["API"]},
            },
        }
    )

    twin = projector.twin_store.get("EMP-001")

    assert twin.entity_type == "DIGITAL_EMPLOYEE"
    assert twin.status == "CAPABILITY_SELECTED"
    assert twin.state["activity_type"] == "THINKING"
    assert twin.state["progress"] == 35
    assert twin.state["work_item_id"] == "WORK-001"
    assert twin.metadata["selected_capabilities"] == ["API"]


def test_workforce_twin_projector_updates_same_employee_without_duplicate():
    projector = WorkforceTwinProjector()

    events = [
        {
            "event_type": "EMPLOYEE_ACTIVITY_RECORDED",
            "payload": {
                "employee_id": "EMP-001",
                "activity_type": "THINKING",
                "status": "CAPABILITY_SELECTED",
                "message": "Thinking",
                "progress": 35,
            },
        },
        {
            "event_type": "EMPLOYEE_ACTIVITY_RECORDED",
            "payload": {
                "employee_id": "EMP-001",
                "activity_type": "EXECUTING",
                "status": "REVIEWING",
                "message": "Executing",
                "progress": 70,
            },
        },
    ]

    projector.project_stream(events)

    snapshot = projector.twin_store.snapshot()

    assert len(snapshot) == 1
    assert snapshot["EMP-001"]["status"] == "REVIEWING"
    assert snapshot["EMP-001"]["state"]["progress"] == 70

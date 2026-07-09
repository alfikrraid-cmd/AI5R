from WORKFORCE.sprint_factory import SprintFactory


def test_sprint_factory_manufactures_sprint_asset():
    result = SprintFactory().manufacture(
        objective="Build login system",
        organization_id="ORG-AI5R",
        department_id="IT",
    )

    sprint = result["asset"]

    assert result["status"] == "MANUFACTURED"
    assert sprint.object_type == "SPRINT_ASSET"
    assert sprint.sprint_id.startswith("SPRINT-")
    assert sprint.objective == "Build login system"
    assert sprint.organization_id == "ORG-AI5R"
    assert sprint.department_id == "IT"
    assert sprint.status == "CREATED"
    assert sprint.assigned_employee_ids == []
    assert sprint.task_ids == []
    assert sprint.manufacturing_order_ids == []
    assert sprint.artifact_ids == []


def test_sprint_factory_requires_objective():
    try:
        SprintFactory().manufacture(
            objective="",
            organization_id="ORG-AI5R",
            department_id="IT",
        )
    except ValueError as exc:
        assert "objective is required" in str(exc)
    else:
        raise AssertionError("Expected sprint manufacture to fail")


def test_sprint_asset_can_track_tasks_employees_orders_and_artifacts():
    sprint = SprintFactory().manufacture(
        objective="Build authentication",
        organization_id="ORG-AI5R",
        department_id="IT",
    )["asset"]

    sprint.add_task("TASK-001")
    sprint.assign_employee("EMP-001")
    sprint.add_manufacturing_order("MO-001")
    sprint.add_artifact("ART-001")

    assert sprint.task_ids == ["TASK-001"]
    assert sprint.assigned_employee_ids == ["EMP-001"]
    assert sprint.manufacturing_order_ids == ["MO-001"]
    assert sprint.artifact_ids == ["ART-001"]

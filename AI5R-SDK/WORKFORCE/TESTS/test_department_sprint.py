from WORKFORCE.department_factory import DepartmentFactory


def test_department_can_start_sprint():
    department = DepartmentFactory().manufacture(
        department_name="IT",
        organization_id="ORG-AI5R",
    )["asset"]

    result = department.start_sprint(
        objective="Build login system",
    )

    sprint = result["sprint"]

    assert result["status"] == "SPRINT_STARTED"
    assert sprint.objective == "Build login system"
    assert sprint.organization_id == "ORG-AI5R"
    assert sprint.department_id == department.department_id
    assert sprint.sprint_id in department.sprint_ids


def test_department_start_sprint_keeps_metadata():
    department = DepartmentFactory().manufacture(
        department_name="IT",
        organization_id="ORG-AI5R",
    )["asset"]

    result = department.start_sprint(
        objective="Build dashboard",
        metadata={
            "priority": "HIGH",
            "source": "WF-003",
        },
    )

    sprint = result["sprint"]

    assert sprint.metadata["priority"] == "HIGH"
    assert sprint.metadata["source"] == "WF-003"


def test_department_does_not_duplicate_started_sprint_id():
    department = DepartmentFactory().manufacture(
        department_name="IT",
        organization_id="ORG-AI5R",
    )["asset"]

    result = department.start_sprint(
        objective="Build API",
    )

    sprint = result["sprint"]

    department.add_sprint(sprint.sprint_id)

    assert department.sprint_ids == [sprint.sprint_id]

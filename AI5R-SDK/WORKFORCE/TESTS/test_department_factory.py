from WORKFORCE.department_factory import DepartmentFactory


def test_department_factory_manufactures_department_asset():
    result = DepartmentFactory().manufacture(
        department_name="IT",
        organization_id="ORG-AI5R",
    )

    department = result["asset"]

    assert result["status"] == "MANUFACTURED"
    assert department.object_type == "DEPARTMENT"
    assert department.department_id.startswith("DEPT-")
    assert department.department_name == "IT"
    assert department.organization_id == "ORG-AI5R"
    assert department.status == "ACTIVE"
    assert department.employee_ids == []
    assert department.sprint_ids == []
    assert department.capability_ids == []


def test_department_factory_requires_name():
    try:
        DepartmentFactory().manufacture(
            department_name="",
            organization_id="ORG-AI5R",
        )
    except ValueError as exc:
        assert "Department name is required" in str(exc)
    else:
        raise AssertionError("Expected department manufacture to fail")


def test_department_can_track_employees_sprints_and_capabilities():
    department = DepartmentFactory().manufacture(
        department_name="IT",
        organization_id="ORG-AI5R",
    )["asset"]

    department.add_employee("EMP-001")
    department.add_sprint("SPRINT-001")
    department.add_capability("SOFTWARE_DELIVERY")

    assert department.employee_ids == ["EMP-001"]
    assert department.sprint_ids == ["SPRINT-001"]
    assert department.capability_ids == ["SOFTWARE_DELIVERY"]


def test_department_does_not_duplicate_relationships():
    department = DepartmentFactory().manufacture(
        department_name="IT",
        organization_id="ORG-AI5R",
    )["asset"]

    department.add_employee("EMP-001")
    department.add_employee("EMP-001")
    department.add_sprint("SPRINT-001")
    department.add_sprint("SPRINT-001")
    department.add_capability("SOFTWARE_DELIVERY")
    department.add_capability("SOFTWARE_DELIVERY")

    assert department.employee_ids == ["EMP-001"]
    assert department.sprint_ids == ["SPRINT-001"]
    assert department.capability_ids == ["SOFTWARE_DELIVERY"]

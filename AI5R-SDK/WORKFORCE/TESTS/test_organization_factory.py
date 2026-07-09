from WORKFORCE.organization_factory import OrganizationFactory


def test_organization_factory_manufactures_organization_asset():
    result = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )

    organization = result["asset"]

    assert result["status"] == "MANUFACTURED"
    assert organization.object_type == "ORGANIZATION"
    assert organization.organization_id.startswith("ORG-")
    assert organization.organization_name == "AI5R"
    assert organization.status == "ACTIVE"
    assert organization.department_ids == []
    assert organization.employee_ids == []
    assert organization.sprint_ids == []


def test_organization_factory_requires_name():
    try:
        OrganizationFactory().manufacture(
            organization_name="",
        )
    except ValueError as exc:
        assert "Organization name is required" in str(exc)
    else:
        raise AssertionError("Expected organization manufacture to fail")


def test_organization_can_track_departments_employees_and_sprints():
    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    organization.add_department("DEPT-001")
    organization.add_employee("EMP-001")
    organization.add_sprint("SPRINT-001")

    assert organization.department_ids == ["DEPT-001"]
    assert organization.employee_ids == ["EMP-001"]
    assert organization.sprint_ids == ["SPRINT-001"]


def test_organization_does_not_duplicate_relationships():
    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    organization.add_department("DEPT-001")
    organization.add_department("DEPT-001")
    organization.add_employee("EMP-001")
    organization.add_employee("EMP-001")
    organization.add_sprint("SPRINT-001")
    organization.add_sprint("SPRINT-001")

    assert organization.department_ids == ["DEPT-001"]
    assert organization.employee_ids == ["EMP-001"]
    assert organization.sprint_ids == ["SPRINT-001"]

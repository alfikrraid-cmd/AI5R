from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.organization_factory import OrganizationFactory


def test_it_department_pack_manufactures_department_and_employees():
    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    result = ITDepartmentPack().manufacture(organization)

    department = result["department"]
    employees = result["employees"]

    assert result["status"] == "MANUFACTURED"
    assert department.department_name == "IT"
    assert department.department_id in organization.department_ids
    assert len(employees) == 9
    assert len(department.employee_ids) == 9
    assert len(organization.employee_ids) == 9


def test_it_department_pack_contains_required_roles():
    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    result = ITDepartmentPack().manufacture(organization)

    position_ids = [
        employee.position_id
        for employee in result["employees"]
    ]

    assert "CTO" in position_ids
    assert "PROJECT_MANAGER" in position_ids
    assert "SOLUTION_ARCHITECT" in position_ids
    assert "BACKEND_ENGINEER" in position_ids
    assert "FRONTEND_ENGINEER" in position_ids
    assert "QA_ENGINEER" in position_ids
    assert "DEVOPS_ENGINEER" in position_ids
    assert "SECURITY_ENGINEER" in position_ids
    assert "DOCUMENTATION_ENGINEER" in position_ids


def test_it_department_employees_have_department_metadata():
    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    result = ITDepartmentPack().manufacture(organization)

    department = result["department"]

    for employee in result["employees"]:
        assert employee.metadata["department_id"] == department.department_id
        assert employee.metadata["department_name"] == "IT"
        assert employee.employee_id in department.employee_ids
        assert employee.employee_id in organization.employee_ids

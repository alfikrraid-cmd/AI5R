from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.organization_factory import OrganizationFactory
from WORKFORCE.project_manager_capability import ProjectManagerCapability


def test_project_manager_assigns_tasks():

    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    pack = ITDepartmentPack().manufacture(organization)

    department = pack["department"]

    sprint = department.start_sprint(
        objective="Build Login API",
    )["sprint"]

    employees = pack["employees"]

    pm = [
        employee
        for employee in employees
        if employee.position_id == "PROJECT_MANAGER"
    ][0]

    capability = ProjectManagerCapability()

    breakdown = capability.breakdown_sprint(
        pm,
        sprint,
    )

    assignment = capability.assign_tasks(
        pm,
        breakdown["tasks"],
        employees,
    )

    assert assignment["status"] == "ASSIGNMENT_COMPLETED"

    assigned = [
        a
        for a in assignment["assignments"]
        if a["status"] == "ASSIGNED"
    ]

    assert len(assigned) == 6

    for task in breakdown["tasks"]:
        assert task.assigned_employee_id is not None
        assert task.status == "ASSIGNED"

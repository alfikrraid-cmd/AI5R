from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.organization_factory import OrganizationFactory
from WORKFORCE.project_manager_capability import ProjectManagerCapability


def _build_it_department_with_sprint():
    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    pack = ITDepartmentPack().manufacture(organization)
    department = pack["department"]

    sprint = department.start_sprint(
        objective="Build login system",
    )["sprint"]

    project_manager = [
        employee
        for employee in pack["employees"]
        if employee.position_id == "PROJECT_MANAGER"
    ][0]

    return project_manager, sprint


def test_project_manager_breaks_down_sprint_into_tasks():
    project_manager, sprint = _build_it_department_with_sprint()

    result = ProjectManagerCapability().breakdown_sprint(
        project_manager=project_manager,
        sprint=sprint,
    )

    tasks = result["tasks"]

    assert result["status"] == "TASKS_CREATED"
    assert result["sprint_id"] == sprint.sprint_id
    assert result["project_manager_id"] == project_manager.employee_id
    assert len(tasks) == 6
    assert len(sprint.task_ids) == 6


def test_task_breakdown_contains_required_positions():
    project_manager, sprint = _build_it_department_with_sprint()

    result = ProjectManagerCapability().breakdown_sprint(
        project_manager=project_manager,
        sprint=sprint,
    )

    assigned_positions = [
        task.assigned_position_id
        for task in result["tasks"]
    ]

    assert "SOLUTION_ARCHITECT" in assigned_positions
    assert "BACKEND_ENGINEER" in assigned_positions
    assert "FRONTEND_ENGINEER" in assigned_positions
    assert "QA_ENGINEER" in assigned_positions
    assert "DEVOPS_ENGINEER" in assigned_positions
    assert "DOCUMENTATION_ENGINEER" in assigned_positions


def test_only_project_manager_can_break_down_sprint():
    project_manager, sprint = _build_it_department_with_sprint()
    project_manager.position_id = "BACKEND_ENGINEER"

    try:
        ProjectManagerCapability().breakdown_sprint(
            project_manager=project_manager,
            sprint=sprint,
        )
    except ValueError as exc:
        assert "Only PROJECT_MANAGER" in str(exc)
    else:
        raise AssertionError("Expected non-project-manager breakdown to fail")


def test_project_manager_requires_task_breakdown_capability():
    project_manager, sprint = _build_it_department_with_sprint()
    project_manager.capability_ids = []

    try:
        ProjectManagerCapability().breakdown_sprint(
            project_manager=project_manager,
            sprint=sprint,
        )
    except ValueError as exc:
        assert "TASK_BREAKDOWN" in str(exc)
    else:
        raise AssertionError("Expected missing capability to fail")

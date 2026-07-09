from WORKFORCE.department_factory import DepartmentFactory
from WORKFORCE.work_item import WorkItem


def test_sprint_can_store_work_items():
    department = DepartmentFactory().manufacture(
        department_name="IT",
        organization_id="ORG-AI5R",
    )["asset"]

    sprint = department.start_sprint(
        objective="Build Login",
    )["sprint"]

    item = WorkItem(
        title="Backend API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    sprint.add_work_item(item)

    assert len(sprint.work_items) == 1
    assert sprint.work_items[0].title == "Backend API"
    assert item.work_item_id in sprint.task_ids


def test_project_manager_breakdown_adds_work_items_to_sprint():
    from WORKFORCE.it_department_pack import ITDepartmentPack
    from WORKFORCE.organization_factory import OrganizationFactory
    from WORKFORCE.project_manager_capability import ProjectManagerCapability

    organization = OrganizationFactory().manufacture(
        organization_name="AI5R",
    )["asset"]

    pack = ITDepartmentPack().manufacture(organization)
    department = pack["department"]
    sprint = department.start_sprint(
        objective="Build Login API",
    )["sprint"]

    pm = [
        employee
        for employee in pack["employees"]
        if employee.position_id == "PROJECT_MANAGER"
    ][0]

    result = ProjectManagerCapability().breakdown_sprint(
        project_manager=pm,
        sprint=sprint,
    )

    assert result["status"] == "TASKS_CREATED"
    assert len(result["tasks"]) == 6
    assert len(sprint.work_items) == 6
    assert len(sprint.task_ids) == 6

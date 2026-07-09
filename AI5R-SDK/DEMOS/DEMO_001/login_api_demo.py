from WORKFORCE.organization_factory import OrganizationFactory
from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.project_manager_capability import ProjectManagerCapability
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.workforce_manufacturing_adapter import WorkforceManufacturingAdapter
from MANUFACTURING.ORDERS import ManufacturingOrderPriority


def run_demo():
    logs = []

    logs.append("AI5R DIGITAL FACTORY — DEMO-001")
    logs.append("Mission: Build FastAPI Login API")

    organization = OrganizationFactory().manufacture("AI5R")["asset"]
    logs.append("✓ Organization created")

    pack = ITDepartmentPack().manufacture(organization)
    department = pack["department"]
    employees = pack["employees"]
    logs.append("✓ IT Department manufactured")
    logs.append(f"✓ {len(employees)} Digital Employees activated")

    sprint = department.start_sprint("Build FastAPI Login API")["sprint"]
    logs.append("✓ Sprint started")

    pm = [e for e in employees if e.position_id == "PROJECT_MANAGER"][0]
    backend = [e for e in employees if e.position_id == "BACKEND_ENGINEER"][0]

    pm_capability = ProjectManagerCapability()
    breakdown = pm_capability.breakdown_sprint(pm, sprint)
    logs.append(f"✓ Project Manager created {len(breakdown['tasks'])} work items")

    board = WorkBoard()

    backend_work = [
        item for item in sprint.work_items
        if item.assigned_position_id == "BACKEND_ENGINEER"
    ][0]

    board.publish(backend_work)
    logs.append("✓ Backend work item published")

    board.claim(backend, backend_work.work_item_id)
    logs.append("✓ Backend Engineer claimed work item")

    runtime = EmployeeRuntime()
    runtime.receive_work(backend, backend_work)
    think_result = runtime.think(backend, backend_work)
    logs.append("✓ Employee Runtime thinking completed")
    logs.append(
        "✓ Selected capabilities: "
        + ", ".join(think_result.metadata["selected_capabilities"])
    )

    order = WorkforceManufacturingAdapter().create_order(
        employee=backend,
        work_item=backend_work,
        product_type="FASTAPI_SERVICE",
        priority=ManufacturingOrderPriority.HIGH,
    )

    logs.append("✓ Canonical Manufacturing Order created")
    logs.append(f"✓ Order ID: {order.order_id}")
    logs.append("✓ DEMO-001 READY FOR FACTORY EXECUTION")

    return {
        "status": "DEMO_001_COMPLETED",
        "logs": logs,
        "order": order,
    }


if __name__ == "__main__":
    result = run_demo()

    print("")
    print("=" * 56)

    for line in result["logs"]:
        print(line)

    print("=" * 56)
    print("")

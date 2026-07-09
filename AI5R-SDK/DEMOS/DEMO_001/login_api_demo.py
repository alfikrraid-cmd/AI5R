from FACTORY.RUNTIME import FactoryRuntime
from MANUFACTURING.ORDERS import ManufacturingOrderPriority
from WORKFORCE.organization_factory import OrganizationFactory
from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.project_manager_capability import ProjectManagerCapability
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.workforce_event_bus import WorkforceEventBus
from WORKFORCE.mission_orchestrator import MissionOrchestrator
from WORKFORCE.workforce_manufacturing_adapter import WorkforceManufacturingAdapter
from DEMOS.DEMO_001.production_plan import Demo001ProductionPlan
from DIGITAL_TWIN.workforce_twin_projector import WorkforceTwinProjector


def run_demo():
    logs = []

    logs.append("AI5R DIGITAL FACTORY — DEMO-002")
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

    breakdown = ProjectManagerCapability().breakdown_sprint(pm, sprint)
    logs.append(f"✓ Project Manager created {len(breakdown['tasks'])} work items")

    backend_work = [
        item for item in sprint.work_items
        if item.assigned_position_id == "BACKEND_ENGINEER"
    ][0]

    board = WorkBoard()
    board.publish(backend_work)
    logs.append("✓ Backend work item published")

    board.claim(backend, backend_work.work_item_id)
    logs.append("✓ Backend Engineer claimed work item")

    event_bus = WorkforceEventBus()
    activity_registry = EmployeeActivityRegistry(event_bus=event_bus)

    mission_result = MissionOrchestrator(
        activity_registry=activity_registry,
    ).run(
        employee=backend,
        work_item=backend_work,
        mission_id="MISSION-DEMO-002",
    )

    logs.append("✓ Mission Orchestrator completed employee lifecycle")
    logs.append("✓ Activity Timeline recorded")
    logs.append("✓ Runtime phases: " + " → ".join(mission_result.runtime_phases))
    logs.append(
        "✓ Selected capabilities: "
        + ", ".join(backend.metadata.get("selected_capabilities", []))
    )

    order = WorkforceManufacturingAdapter().create_order(
        employee=backend,
        work_item=backend_work,
        product_type="FASTAPI_SERVICE",
        priority=ManufacturingOrderPriority.HIGH,
    )

    logs.append("✓ Canonical Manufacturing Order created")
    logs.append(f"✓ Order ID: {order.order_id}")

    twin_store = WorkforceTwinProjector().project_stream(event_bus.stream())
    logs.append("✓ Digital Twin Snapshot created")

    production_plan = Demo001ProductionPlan().create_from_order(order)
    logs.append("✓ Product Blueprint resolved")
    logs.append("✓ Production Plan created")
    logs.append(f"✓ Planned artifacts: {len(production_plan['artifacts'])}")

    factory = FactoryRuntime().run(
        production_plan=production_plan,
    )

    logs.append("✓ Factory Runtime completed")
    logs.append(f"✓ Workspace: {factory['execution'].workspace['workspace']}")
    logs.append("✓ Build validated")
    logs.append(f"✓ Validation: {factory['validation']['status']}")
    logs.append("✓ ZIP exported")
    logs.append(f"✓ ZIP: {factory['archive']['zip_path']}")
    logs.append("✓ DEMO-002 COMPLETE")

    return {
        "status": "DEMO_002_COMPLETED",
        "logs": logs,
        "organization": organization,
        "department": department,
        "mission": mission_result,
        "order": order,
        "production_plan": production_plan,
        "factory": factory,
        "activity_stream": event_bus.stream(),
        "digital_twin_snapshot": twin_store.snapshot(),
    }


if __name__ == "__main__":
    result = run_demo()

    print("")
    print("=" * 60)
    print("AI5R DIGITAL FACTORY")
    print("=" * 60)

    for line in result["logs"]:
        print(line)

    print("")
    print("DOWNLOADABLE PRODUCT")
    print("-" * 60)
    print(result["factory"]["archive"]["zip_path"])

    print("")
    print("WORKSPACE")
    print("-" * 60)
    print(result["factory"]["execution"].workspace["workspace"])

    print("=" * 60)
    print("")

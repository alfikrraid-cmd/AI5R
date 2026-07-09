from WORKFORCE.organization_factory import OrganizationFactory
from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.project_manager_capability import ProjectManagerCapability
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.mission_orchestrator import MissionOrchestrator
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.workforce_event_bus import WorkforceEventBus
from WORKFORCE.workforce_manufacturing_adapter import WorkforceManufacturingAdapter
from MANUFACTURING.ORDERS import ManufacturingOrderPriority
from DEMOS.DEMO_001.production_plan import Demo001ProductionPlan
from DIGITAL_TWIN.workforce_twin_projector import WorkforceTwinProjector


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

    event_bus = WorkforceEventBus()
    activity_registry = EmployeeActivityRegistry(event_bus=event_bus)
    orchestrator = MissionOrchestrator(activity_registry=activity_registry)
    mission_result = orchestrator.run(
        employee=backend,
        work_item=backend_work,
        mission_id="MISSION-DEMO-001",
    )

    logs.append("✓ Mission Orchestrator completed employee lifecycle")
    logs.append("✓ Activity Timeline recorded")
    logs.append(
        "✓ Runtime phases: "
        + " → ".join(mission_result.runtime_phases)
    )
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

    plan = Demo001ProductionPlan().create_from_order(order)
    logs.append("✓ Product Blueprint resolved")
    logs.append("✓ Production Plan created")
    logs.append(f"✓ Planned artifacts: {len(plan['artifacts'])}")
    logs.append("✓ DEMO-001 READY FOR FACTORY EXECUTION")

    return {
        "status": "DEMO_001_COMPLETED",
        "logs": logs,
        "order": order,
        "production_plan": plan,
        "activity_stream": event_bus.stream(),
        "digital_twin_snapshot": twin_store.snapshot(),
    }


if __name__ == "__main__":
    result = run_demo()

    print("")
    print("=" * 56)

    for line in result["logs"]:
        print(line)

    print("=" * 56)
    print("Digital Twin Snapshot")
    print("-" * 56)
    for entity_id, twin in result.get("digital_twin_snapshot", {}).items():
        print(f"{entity_id} | {twin['entity_type']} | {twin['status']} | {twin['state'].get('progress', 0)}%")
    print("=" * 56)
    print("Activity Timeline")
    print("-" * 56)
    for event in result.get("activity_stream", []):
        payload = event["payload"]
        print(f"{payload['activity_type']} | {payload['status']} | {payload['progress']}% | {payload['message']}")
    print("=" * 56)
    print("")

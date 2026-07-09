from MANUFACTURING.ORDERS import ManufacturingOrderPriority
from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.work_item import WorkItem
from WORKFORCE.workforce_manufacturing_adapter import WorkforceManufacturingAdapter


def test_workforce_adapter_creates_canonical_manufacturing_order():
    board = WorkBoard()

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-001",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["API", "JWT"],
    )["employee"]

    work_item = WorkItem(
        title="Build JWT Login API",
        assigned_position_id="BACKEND_ENGINEER",
        description="Create login endpoint",
    )

    board.publish(work_item)
    board.claim(employee, work_item.work_item_id)

    runtime = EmployeeRuntime()
    runtime.receive_work(employee, work_item)
    runtime.think(employee, work_item)

    order = WorkforceManufacturingAdapter().create_order(
        employee=employee,
        work_item=work_item,
        product_type="FASTAPI_SERVICE",
        priority=ManufacturingOrderPriority.HIGH,
    )

    assert order.order_id.startswith("MO-")
    assert order.product_name == "Build JWT Login API"
    assert order.product_type == "FASTAPI_SERVICE"
    assert order.requested_by == employee.employee_id
    assert order.priority == ManufacturingOrderPriority.HIGH
    assert order.validate() is True
    assert order.requirements["work_item_id"] == work_item.work_item_id
    assert order.requirements["selected_capabilities"] == ["API", "JWT"]
    assert order.metadata["source"] == "WORKFORCE"
    assert work_item.status == "ORDER_CREATED"
    assert work_item.manufacturing_order_id == order.order_id


def test_workforce_adapter_requires_claimed_work_item():
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-002",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    work_item = WorkItem(
        title="Build API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    try:
        WorkforceManufacturingAdapter().create_order(
            employee=employee,
            work_item=work_item,
            product_type="FASTAPI_SERVICE",
        )
    except ValueError as exc:
        assert "must be claimed" in str(exc)
    else:
        raise AssertionError("Expected unclaimed work item to fail")


def test_workforce_adapter_requires_product_type():
    board = WorkBoard()

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-003",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]

    work_item = WorkItem(
        title="Build API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    board.publish(work_item)
    board.claim(employee, work_item.work_item_id)

    try:
        WorkforceManufacturingAdapter().create_order(
            employee=employee,
            work_item=work_item,
            product_type="",
        )
    except ValueError as exc:
        assert "product_type is required" in str(exc)
    else:
        raise AssertionError("Expected missing product_type to fail")

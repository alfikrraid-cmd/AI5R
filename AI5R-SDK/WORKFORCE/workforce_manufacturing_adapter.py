from uuid import uuid4

from MANUFACTURING.ORDERS import (
    ManufacturingOrder,
    ManufacturingOrderPriority,
)
from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.work_item import WorkItem


class WorkforceManufacturingAdapter:
    def create_order(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
        product_type: str,
        priority: ManufacturingOrderPriority = ManufacturingOrderPriority.MEDIUM,
    ) -> ManufacturingOrder:
        if work_item.assigned_employee_id != employee.employee_id:
            raise ValueError("Work item must be claimed by employee before order creation")

        if not product_type:
            raise ValueError("product_type is required")

        order = ManufacturingOrder(
            order_id=f"MO-{uuid4()}",
            product_name=work_item.title,
            product_type=product_type,
            requested_by=employee.employee_id,
            priority=priority,
            requirements={
                "work_item_id": work_item.work_item_id,
                "description": work_item.description,
                "assigned_position_id": work_item.assigned_position_id,
                "selected_capabilities": employee.metadata.get(
                    "selected_capabilities",
                    [],
                ),
            },
            metadata={
                "source": "WORKFORCE",
                "organization_id": employee.organization_id,
                "employee_id": employee.employee_id,
                "position_id": employee.position_id,
            },
        )

        if not order.validate():
            raise ValueError("Generated manufacturing order is invalid")

        work_item.manufacturing_order_id = order.order_id
        work_item.status = "ORDER_CREATED"

        return order

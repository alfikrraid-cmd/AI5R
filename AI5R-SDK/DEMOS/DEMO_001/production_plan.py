from MANUFACTURING.ORDERS import ManufacturingOrder
from DEMOS.DEMO_001.BLUEPRINTS.fastapi_login_api_blueprint import (
    FASTAPI_LOGIN_API_BLUEPRINT,
)


class Demo001ProductionPlan:
    def create_from_order(self, order: ManufacturingOrder) -> dict:
        if order.product_type != FASTAPI_LOGIN_API_BLUEPRINT["product_type"]:
            raise ValueError("Unsupported product_type for DEMO-001")

        return {
            "status": "PRODUCTION_PLAN_CREATED",
            "order_id": order.order_id,
            "product_name": order.product_name,
            "product_type": order.product_type,
            "requested_by": order.requested_by,
            "artifacts": FASTAPI_LOGIN_API_BLUEPRINT["artifacts"],
            "features": FASTAPI_LOGIN_API_BLUEPRINT["features"],
            "requirements": order.requirements,
            "metadata": {
                **order.metadata,
                "blueprint": "FASTAPI_LOGIN_API_BLUEPRINT",
            },
        }

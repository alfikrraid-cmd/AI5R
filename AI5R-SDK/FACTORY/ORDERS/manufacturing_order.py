from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


@dataclass
class ManufacturingOrder:
    order_id: str
    requested_product: str
    customer_request: str
    status: str = "CREATED"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def validate(self) -> bool:
        if not self.order_id:
            raise ValueError("order_id is required")

        if not self.requested_product:
            raise ValueError("requested_product is required")

        if not self.customer_request:
            raise ValueError("customer_request is required")

        if self.status not in [
            "CREATED",
            "VALIDATED",
            "RESOLVED",
            "RUNNING",
            "COMPLETED",
            "FAILED",
        ]:
            raise ValueError("invalid order status")

        return True

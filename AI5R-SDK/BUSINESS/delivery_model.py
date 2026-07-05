from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class DeliveryModel:

    product_code: str

    delivery_code: str

    delivery_name: str

    deployment_type: str

    management_type: str

    service_scope: str

    support_level: str

    object_type: str = "DELIVERY_MODEL"

    status: str = "ACTIVE"

    delivery_id: str = field(
        default_factory=lambda: f"DEL-{uuid4()}"
    )

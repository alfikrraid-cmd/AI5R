from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class BusinessModelObject:

    product_code: str

    product_name: str

    target_customer: str

    revenue_model: str

    delivery_model: str

    support_model: str

    pricing_strategy: str

    object_type: str = "BUSINESS_MODEL"

    status: str = "ACTIVE"

    business_model_id: str = field(
        default_factory=lambda: f"BM-{uuid4()}"
    )

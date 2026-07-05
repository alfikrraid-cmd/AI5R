from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class PricingModel:

    product_code: str

    plan_code: str

    plan_name: str

    billing_cycle: str

    price_amount: float

    currency: str

    included_units: int = 0

    overage_rate: float = 0.0

    object_type: str = "PRICING_MODEL"

    status: str = "ACTIVE"

    pricing_id: str = field(
        default_factory=lambda: f"PRICE-{uuid4()}"
    )

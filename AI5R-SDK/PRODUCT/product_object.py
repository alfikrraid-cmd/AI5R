from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ProductObject:

    product_code: str

    product_name: str

    category: str

    version: str

    description: str

    owner: str

    runtime: str

    status: str = "ACTIVE"

    object_type: str = "PRODUCT"

    product_id: str = field(
        default_factory=lambda: f"PROD-{uuid4()}"
    )

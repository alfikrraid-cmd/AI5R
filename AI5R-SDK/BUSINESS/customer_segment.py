from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class CustomerSegment:

    segment_code: str

    segment_name: str

    description: str

    target_industry: str

    company_size: str

    primary_need: str

    buying_trigger: str

    object_type: str = "CUSTOMER_SEGMENT"

    status: str = "ACTIVE"

    segment_id: str = field(
        default_factory=lambda: f"SEG-{uuid4()}"
    )

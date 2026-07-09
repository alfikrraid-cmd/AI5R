from dataclasses import dataclass, field


@dataclass
class Customer:
    customer_id: str
    name: str
    segment: str = "GENERAL"
    status: str = "LEAD"
    tags: list[str] = field(default_factory=list)

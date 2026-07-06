from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class OrganizationBlueprint:
    blueprint_name: str
    industry: str
    departments: list[str]
    positions: list[str]
    capabilities: list[str]
    workflows: list[str] = field(default_factory=list)
    status: str = "DRAFT"
    blueprint_id: str = field(default_factory=lambda: f"BP-{uuid4()}")

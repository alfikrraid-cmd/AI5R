from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from CORE.SPECIFICATION.specification_status import SpecificationStatus


@dataclass
class Specification:

    specification_type: str

    specification_name: str

    specification_id: str = field(
        default_factory=lambda: f"SPEC-{uuid4()}"
    )

    version: str = "1.0.0"

    status: SpecificationStatus = SpecificationStatus.DRAFT

    metadata: dict = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def approve(self):
        self.status = SpecificationStatus.APPROVED

    def freeze(self):
        self.status = SpecificationStatus.FROZEN

    def deprecate(self):
        self.status = SpecificationStatus.DEPRECATED

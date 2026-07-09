from dataclasses import dataclass, field
from datetime import datetime, UTC

from BUSINESS.COMMERCIAL.CONTRACT.contract_party import ContractParty
from BUSINESS.COMMERCIAL.CONTRACT.contract_status import ContractStatus


@dataclass
class Contract:
    contract_id: str
    customer_id: str
    title: str
    parties: list[ContractParty] = field(default_factory=list)
    value: float = 0
    currency: str = "IDR"
    status: ContractStatus = ContractStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def touch(self):
        self.updated_at = datetime.now(UTC).isoformat()

    @property
    def is_active(self):
        return self.status == ContractStatus.ACTIVE

from dataclasses import dataclass


@dataclass(frozen=True)
class ContractParty:
    party_id: str
    name: str
    role: str

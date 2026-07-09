from BUSINESS.COMMERCIAL.CONTRACT.contract import Contract
from BUSINESS.COMMERCIAL.CONTRACT.contract_party import ContractParty
from BUSINESS.COMMERCIAL.CONTRACT.contract_status import ContractStatus


class ContractEngine:
    def create(
        self,
        contract_id: str,
        customer_id: str,
        title: str,
        value: float = 0,
        currency: str = "IDR",
    ) -> Contract:
        if not contract_id:
            raise ValueError("Contract ID is required")

        if not customer_id:
            raise ValueError("Customer ID is required")

        if value < 0:
            raise ValueError("Contract value cannot be negative")

        return Contract(
            contract_id=contract_id,
            customer_id=customer_id,
            title=title,
            value=value,
            currency=currency,
        )

    def add_party(self, contract: Contract, party: ContractParty) -> Contract:
        if any(existing.party_id == party.party_id for existing in contract.parties):
            raise ValueError("Duplicate party")

        contract.parties.append(party)
        contract.touch()
        return contract

    def submit_for_review(self, contract: Contract) -> Contract:
        self._transition(contract, ContractStatus.REVIEW, [ContractStatus.DRAFT])
        return contract

    def approve(self, contract: Contract) -> Contract:
        self._transition(contract, ContractStatus.APPROVED, [ContractStatus.REVIEW])
        return contract

    def activate(self, contract: Contract) -> Contract:
        self._transition(contract, ContractStatus.ACTIVE, [ContractStatus.APPROVED])
        return contract

    def complete(self, contract: Contract) -> Contract:
        self._transition(contract, ContractStatus.COMPLETED, [ContractStatus.ACTIVE])
        return contract

    def cancel(self, contract: Contract) -> Contract:
        self._transition(
            contract,
            ContractStatus.CANCELLED,
            [ContractStatus.DRAFT, ContractStatus.REVIEW, ContractStatus.APPROVED],
        )
        return contract

    def terminate(self, contract: Contract) -> Contract:
        self._transition(contract, ContractStatus.TERMINATED, [ContractStatus.ACTIVE])
        return contract

    def _transition(
        self,
        contract: Contract,
        target_status: ContractStatus,
        allowed_from: list[ContractStatus],
    ):
        if contract.status not in allowed_from:
            raise ValueError(
                f"Invalid transition from {contract.status} to {target_status}"
            )

        contract.status = target_status
        contract.touch()

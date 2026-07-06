from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Delegation:
    delegator: str
    delegatee: str
    task: str
    status: str = "DELEGATED"
    delegation_id: str = field(default_factory=lambda: f"DLG-{uuid4()}")
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class DelegationRuntime:

    def __init__(self):
        self._delegations = []

    def delegate(
        self,
        delegator: str,
        delegatee: str,
        task: str,
    ):
        delegation = Delegation(
            delegator=delegator,
            delegatee=delegatee,
            task=task,
        )

        self._delegations.append(delegation)

        return {
            "status": "DELEGATED",
            "delegation": delegation,
        }

    def list_all(self):
        return self._delegations

    def list_by_delegator(self, delegator: str):
        return [
            delegation
            for delegation in self._delegations
            if delegation.delegator == delegator
        ]

    def list_by_delegatee(self, delegatee: str):
        return [
            delegation
            for delegation in self._delegations
            if delegation.delegatee == delegatee
        ]

    def complete(self, delegation_id: str):
        for delegation in self._delegations:
            if delegation.delegation_id == delegation_id:
                delegation.status = "COMPLETED"
                return {
                    "status": "COMPLETED",
                    "delegation": delegation,
                }

        return {
            "status": "NOT_FOUND",
            "delegation": None,
        }

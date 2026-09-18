from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INVALID = "INVALID"


class ChiefApprovalRequiredError(ValueError):
    """Raised when production-impacting release lacks valid human Chief approval."""

    pass


VALID_CHIEF_ROLES = {
    "CHIEF",
    "CHIEF_ARCHITECT",
    "CEO",
    "FOUNDER",
    "CHIEF_EXECUTIVE_OFFICER",
}


@dataclass
class Approver:
    employee_id: str
    role: str
    approval_limit: float = 0.0
    is_human: bool = False
    authority_level: int = 0
    name: str = ""


@dataclass
class ApprovalRecord:
    approval_id: str = field(default_factory=lambda: f"APPR-{uuid4().hex[:12].upper()}")
    employee_id: str = ""
    supervisor_id: str = ""
    approver_role: str = ""
    is_human: bool = False
    decision: str = "PENDING"
    request_amount: float = 0.0
    target_id: str | None = None
    timestamp: str = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        return self.decision


@dataclass
class ChiefApprovalRecord:
    work_item_id: str
    approver_id: str
    approver_role: str
    is_human: bool
    status: str = "APPROVED"
    approval_id: str = field(default_factory=lambda: f"CHIEF-APPR-{uuid4().hex[:12].upper()}")
    approved_at: str = field(default_factory=_now)
    scope: str = "PRODUCTION_DEPLOYMENT"
    metadata: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "work_item_id": self.work_item_id,
            "approver_id": self.approver_id,
            "approver_role": self.approver_role,
            "is_human": self.is_human,
            "status": self.status,
            "approved_at": self.approved_at,
            "scope": self.scope,
            "metadata": dict(self.metadata),
        }


def is_production_work_item(work_item: Any) -> bool:
    """Inspects work item to determine whether it is production-impacting."""
    if not hasattr(work_item, "metadata") or not isinstance(work_item.metadata, dict):
        return False

    meta = work_item.metadata
    if meta.get("is_production") is True:
        return True
    if meta.get("requires_chief_approval") is True:
        return True
    if meta.get("production_impact") is True:
        return True

    env = str(meta.get("environment", "")).lower()
    target_env = str(meta.get("target_environment", "")).lower()
    deploy_target = str(meta.get("deploy_target", "")).lower()

    if "production" in (env, target_env, deploy_target):
        return True

    return False


def validate_chief_approval(work_item: Any, approval: Any) -> None:
    """Validate that production release has explicit, valid, human Chief approval.

    Enforces FAIL CLOSED:
    - Missing approval -> DENIED
    - String / unstructured approval -> DENIED
    - Non-human / AI employee approval -> DENIED
    - Non-Chief role approval -> DENIED
    - Mismatched work_item_id -> DENIED
    - Status != APPROVED (PENDING, REJECTED, etc.) -> DENIED
    """
    work_item_id = (
        getattr(work_item, "work_item_id", None)
        or getattr(work_item, "task_id", None)
        or str(work_item)
    )

    if approval is None:
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            "Human Chief approval is MISSING. Production deployments require explicit human Chief sign-off."
        )

    # Reject magic strings or unstructured objects
    if isinstance(approval, str):
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            f"Unstructured string approval ('{approval}') is INVALID. "
            "Approval must be an explicit structured ChiefApprovalRecord with provenance."
        )

    if not isinstance(approval, (ChiefApprovalRecord, ApprovalRecord, dict)):
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            f"Approval object of type {type(approval).__name__} is INVALID."
        )

    # Extract provenance fields whether dataclass or dict
    if isinstance(approval, dict):
        approver_id = approval.get("approver_id") or approval.get("supervisor_id", "")
        approver_role = str(approval.get("approver_role", "")).upper()
        is_human = approval.get("is_human", False)
        status = str(approval.get("status") or approval.get("decision", "")).upper()
        record_work_item_id = approval.get("work_item_id") or approval.get("target_id")
    else:
        approver_id = getattr(approval, "approver_id", "") or getattr(approval, "supervisor_id", "")
        approver_role = str(getattr(approval, "approver_role", "")).upper()
        is_human = getattr(approval, "is_human", False)
        status = str(getattr(approval, "status", "") or getattr(approval, "decision", "")).upper()
        record_work_item_id = getattr(approval, "work_item_id", None) or getattr(
            approval, "target_id", None
        )

    # 1. Target ID verification (if present on record)
    if record_work_item_id and record_work_item_id != work_item_id:
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            f"Approval target '{record_work_item_id}' does not match work item '{work_item_id}'."
        )

    # 2. Status verification
    if status == "PENDING":
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            "Chief approval is PENDING. Production release requires an APPROVED decision."
        )
    if status == "REJECTED":
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            "Chief approval was REJECTED. Production release is denied."
        )
    if status != "APPROVED":
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            f"Approval status '{status}' is INVALID. Only 'APPROVED' grants release."
        )

    # 3. Human identity verification (AI employees cannot self-approve)
    if not is_human:
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            f"Approver '{approver_id}' (role: {approver_role or 'UNKNOWN'}) is not marked as human. "
            "AI employees (QA, PM, CTO, DevOps, or self) CANNOT approve production releases. "
            "Explicit human Chief approval is mandatory."
        )

    # 4. Role authority verification
    if not approver_role or approver_role not in VALID_CHIEF_ROLES:
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            f"Approver role '{approver_role}' lacks Chief release authority. "
            f"Must be one of: {', '.join(sorted(VALID_CHIEF_ROLES))}."
        )

    # 5. Approver identity verification
    if not approver_id:
        raise ChiefApprovalRequiredError(
            f"Production release blocked for work item '{work_item_id}': "
            "Approver identity is MISSING in approval record."
        )


class ApprovalChainRuntime:
    """Runtime for workforce organizational approvals and Chief release gating."""

    def __init__(self, approvers: list[Approver] | None = None) -> None:
        self._approvers: dict[str, Approver] = {}
        self._decisions: dict[str, ApprovalRecord] = {}
        self._chief_approvals: dict[str, ChiefApprovalRecord] = {}

        if approvers:
            for approver in approvers:
                self.register_approver(approver)
        else:
            self.register_approver(
                Approver(
                    employee_id="ID-PROJECT_MANAGER",
                    role="PROJECT_MANAGER",
                    approval_limit=1000.0,
                    is_human=False,
                    authority_level=1,
                    name="AI Project Manager",
                )
            )
            self.register_approver(
                Approver(
                    employee_id="ID-CTO",
                    role="CTO",
                    approval_limit=10000.0,
                    is_human=False,
                    authority_level=2,
                    name="AI CTO",
                )
            )
            self.register_approver(
                Approver(
                    employee_id="raid",
                    role="CHIEF_ARCHITECT",
                    approval_limit=float("inf"),
                    is_human=True,
                    authority_level=99,
                    name="Chief Architect",
                )
            )

    def register_approver(self, approver: Approver) -> None:
        self._approvers[approver.employee_id] = approver

    def resolve_approver(self, request_amount: float) -> Approver | None:
        """Resolve the lowest-tier eligible approver whose limit covers request_amount."""
        eligible = [
            app
            for app in self._approvers.values()
            if app.approval_limit >= request_amount
        ]
        if not eligible:
            return None
        return min(eligible, key=lambda app: app.approval_limit)

    def record_decision(
        self,
        employee_id: str,
        supervisor_id: str,
        decision: Any,
        request_amount: float = 0.0,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRecord:
        approver = self._approvers.get(supervisor_id)
        approver_role = approver.role if approver else ""
        is_human = approver.is_human if approver else False

        record = ApprovalRecord(
            employee_id=employee_id,
            supervisor_id=supervisor_id,
            approver_role=approver_role,
            is_human=is_human,
            decision=str(decision),
            request_amount=request_amount,
            target_id=target_id,
            metadata=metadata or {},
        )
        self._decisions[record.approval_id] = record
        return record

    def request_chief_approval(
        self,
        work_item_id: str,
        requester_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> ChiefApprovalRecord:
        record = ChiefApprovalRecord(
            work_item_id=work_item_id,
            approver_id="",
            approver_role="CHIEF_ARCHITECT",
            is_human=True,
            status="PENDING",
            metadata={
                "requester_id": requester_id,
                **(metadata or {}),
            },
        )
        self._chief_approvals[work_item_id] = record
        return record

    def grant_chief_approval(
        self,
        work_item_id: str,
        approver_id: str = "raid",
        approver_role: str = "CHIEF_ARCHITECT",
        is_human: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ChiefApprovalRecord:
        role_upper = approver_role.upper()
        if not is_human or role_upper not in VALID_CHIEF_ROLES:
            record = ChiefApprovalRecord(
                work_item_id=work_item_id,
                approver_id=approver_id,
                approver_role=approver_role,
                is_human=is_human,
                status="INVALID",
                metadata=metadata or {},
            )
            self._chief_approvals[work_item_id] = record
            validate_chief_approval(work_item_id, record)

        record = ChiefApprovalRecord(
            work_item_id=work_item_id,
            approver_id=approver_id,
            approver_role=approver_role,
            is_human=True,
            status="APPROVED",
            metadata=metadata or {},
        )
        self._chief_approvals[work_item_id] = record
        return record

    def reject_chief_approval(
        self,
        work_item_id: str,
        approver_id: str = "raid",
        approver_role: str = "CHIEF_ARCHITECT",
        is_human: bool = True,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ChiefApprovalRecord:
        record = ChiefApprovalRecord(
            work_item_id=work_item_id,
            approver_id=approver_id,
            approver_role=approver_role,
            is_human=is_human,
            status="REJECTED",
            metadata={"reason": reason, **(metadata or {})},
        )
        self._chief_approvals[work_item_id] = record
        return record

    def get_chief_approval(self, work_item_id: str) -> ChiefApprovalRecord | None:
        return self._chief_approvals.get(work_item_id)


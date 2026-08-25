"""MWO-LTSA-AUTH-003A-FINAL -- User Administration: delegation
authorization and last-SUPERUSER safety.

Pure logic, zero DB I/O (same "inject the repository, decide in pure
functions" discipline auth_service.py/installation_review_service.py
already establish) -- routers/admin_users.py is the one caller that wires
this to a real AuthRepository-backed count/lookup.
"""

from __future__ import annotations

from .auth_service import can_delegate_role


class DelegationDeniedError(PermissionError):
    """Raised when actor_role is not authorized to manage target_role
    accounts (see auth_service.DELEGATION_SCOPE)."""


class LastSuperuserError(ValueError):
    """Raised when an action would leave the system with zero active
    SUPERUSER authority (Hard Rule: "prevent the system from ending with
    zero active SUPERUSER authority")."""


def authorize_user_management(actor_role: str, target_role: str) -> None:
    """The one gate every user-administration action (create, status
    change, role change, password reset) must call before touching a
    target user -- raises DelegationDeniedError rather than silently
    allowing an out-of-scope action. SUPERUSER-vs-SUPERUSER and
    TAP_ADMIN-vs-TAP_ENGINEER/JOHN_CRANE_ENGINEER/PERTAMINA_* are legitimate;
    TAP_ADMIN managing SUPERUSER or TAP_ADMIN is not."""
    if not can_delegate_role(actor_role, target_role):
        raise DelegationDeniedError(f"{actor_role} is not authorized to manage {target_role} accounts")


def guard_last_superuser(*, target_is_active_superuser: bool, active_superuser_count: int, action: str) -> None:
    """Call before disabling a user or demoting a user away from
    SUPERUSER (self-demote included -- actor and target may be the same
    person; this function does not care who initiated the action, only
    whether the target is the last active SUPERUSER). No delete path
    exists in this domain (Phase 7's own "prefer deactivate over
    destructive delete"), so disable/demote are the only two actions that
    can ever reduce SUPERUSER count.

    active_superuser_count is the count BEFORE this action; refuses only
    when the target itself is one of those (fewer than or equal to 1)
    remaining active SUPERUSERs -- a second SU may always safely lose
    authority once at least 2 exist.
    """
    if target_is_active_superuser and active_superuser_count <= 1:
        raise LastSuperuserError(f"cannot {action}: this is the last active SUPERUSER account")


__all__ = [
    "DelegationDeniedError",
    "LastSuperuserError",
    "authorize_user_management",
    "guard_last_superuser",
]

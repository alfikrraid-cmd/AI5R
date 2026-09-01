"""MWO-LTSA-AUTH-003A-FINAL -- pure-logic coverage for auth_admin_service.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.auth_admin_service import (  # noqa: E402
    DelegationDeniedError,
    LastSuperuserError,
    authorize_user_management,
    guard_last_superuser,
)


class TestAuthorizeUserManagement:
    def test_superuser_may_manage_any_role(self):
        for target in ("SUPERUSER", "TAP_ADMIN", "TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
            authorize_user_management("SUPERUSER", target)  # must not raise

    def test_tap_admin_may_manage_ordinary_operational_roles(self):
        for target in ("TAP_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
            authorize_user_management("TAP_ADMIN", target)  # must not raise

    def test_tap_admin_cannot_manage_superuser(self):
        with pytest.raises(DelegationDeniedError):
            authorize_user_management("TAP_ADMIN", "SUPERUSER")

    def test_tap_admin_may_manage_john_crane_engineer(self):
        # Commit 62bebce5 ("fix(auth): make TAP admin user management
        # usable", 2026-08-25) deliberately reversed the earlier
        # MWO-LTSA-AUTH-003A-FINAL exclusion of JOHN_CRANE_ENGINEER from
        # TAP_ADMIN's DELEGATION_SCOPE -- see auth_service.py's own
        # current DELEGATION_SCOPE comment and auth_admin_service.py's
        # own authorize_user_management docstring, both updated in that
        # same commit. TAP_ADMIN still can never manage SUPERUSER/
        # TAP_ADMIN (see test above), and the organization-boundary check
        # (admin_users.py's _require_same_organization, added in that
        # same commit) independently constrains this to same-org JC
        # accounts only -- this test covers delegation scope only, not
        # the org boundary (see test_admin_users_router.py for that).
        authorize_user_management("TAP_ADMIN", "JOHN_CRANE_ENGINEER")  # must not raise

    def test_tap_engineer_cannot_manage_anyone(self):
        with pytest.raises(DelegationDeniedError):
            authorize_user_management("TAP_ENGINEER", "PERTAMINA_VIEWER")

    def test_john_crane_engineer_cannot_manage_anyone(self):
        with pytest.raises(DelegationDeniedError):
            authorize_user_management("JOHN_CRANE_ENGINEER", "PERTAMINA_VIEWER")


class TestGuardLastSuperuser:
    def test_disabling_a_non_superuser_is_always_safe(self):
        guard_last_superuser(target_is_active_superuser=False, active_superuser_count=1, action="disable")

    def test_disabling_second_of_two_superusers_is_safe(self):
        guard_last_superuser(target_is_active_superuser=True, active_superuser_count=2, action="disable")

    def test_disabling_the_last_active_superuser_is_refused(self):
        with pytest.raises(LastSuperuserError):
            guard_last_superuser(target_is_active_superuser=True, active_superuser_count=1, action="disable")

    def test_demoting_the_last_active_superuser_is_refused(self):
        with pytest.raises(LastSuperuserError):
            guard_last_superuser(target_is_active_superuser=True, active_superuser_count=1, action="demote")

    def test_self_demote_as_last_superuser_is_refused(self):
        # guard_last_superuser does not distinguish actor from target --
        # a self-demote of the last SU is refused exactly like any other.
        with pytest.raises(LastSuperuserError):
            guard_last_superuser(target_is_active_superuser=True, active_superuser_count=1, action="self-demote")

    def test_zero_count_is_also_refused_defensively(self):
        with pytest.raises(LastSuperuserError):
            guard_last_superuser(target_is_active_superuser=True, active_superuser_count=0, action="disable")

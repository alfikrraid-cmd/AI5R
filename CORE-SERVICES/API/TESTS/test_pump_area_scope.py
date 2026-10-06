"""MWO-LTSA-AUTH-DATA-SCOPE-CLOSURE-001 -- pure-logic coverage for
API.auth_service.resolve_area_scope and API.pump_area_scope's filter/
check primitives. No database, no HTTP -- router-level enforcement is
proven separately in BACKEND-API/TESTS/test_pumps_area_scope_router.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity, resolve_area_scope  # noqa: E402
from API.pump_area_scope import (  # noqa: E402
    AREA_CODES,
    MA_AREA_GROUPS,
    filter_records_by_scope,
    is_area_in_scope,
)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="u1", email="u1@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


class TestResolveAreaScopeUnrestrictedRoles:
    def test_superuser_is_unrestricted(self):
        assert resolve_area_scope(_identity("SUPERUSER")) is None

    def test_tap_admin_is_unrestricted(self):
        assert resolve_area_scope(_identity("TAP_ADMIN")) is None

    def test_tap_engineer_is_unrestricted(self):
        assert resolve_area_scope(_identity("TAP_ENGINEER")) is None

    def test_john_crane_engineer_is_unrestricted(self):
        assert resolve_area_scope(_identity("JOHN_CRANE_ENGINEER")) is None

    def test_unrestricted_regardless_of_a_stray_scope_value(self):
        # Area/MA scope must never accidentally NARROW a role this MWO
        # says is always ALL.
        identity = _identity("TAP_ENGINEER", data_scope_type="AREA", data_scope_value="HOC")
        assert resolve_area_scope(identity) is None


class TestResolveAreaScopePertaminaByArea:
    def test_hoc_scoped_engineer(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC")
        assert resolve_area_scope(identity) == frozenset({"HOC"})

    def test_hsc_scoped_viewer(self):
        identity = _identity("PERTAMINA_VIEWER", data_scope_type="AREA", data_scope_value="HSC")
        assert resolve_area_scope(identity) == frozenset({"HSC"})

    def test_s_pakning_scoped(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="S_PAKNING")
        assert resolve_area_scope(identity) == frozenset({"S_PAKNING"})

    def test_hcc_scoped(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HCC")
        assert resolve_area_scope(identity) == frozenset({"HCC"})

    def test_om_scoped(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="OM")
        assert resolve_area_scope(identity) == frozenset({"OM"})

    def test_utl_scoped(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="UTL")
        assert resolve_area_scope(identity) == frozenset({"UTL"})

    def test_all_six_area_codes_are_the_ones_this_mwo_names(self):
        assert AREA_CODES == frozenset({"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"})


class TestResolveAreaScopePertaminaByMA:
    def test_ma1_covers_hoc(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA1")
        assert resolve_area_scope(identity) == frozenset({"HOC"})

    def test_ma2_covers_exactly_hsc_s_pakning_hcc(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA2")
        assert resolve_area_scope(identity) == frozenset({"HSC", "S_PAKNING", "HCC"})

    def test_ma3_covers_utl(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA3")
        assert resolve_area_scope(identity) == frozenset({"UTL"})

    def test_ma4_covers_om(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA4")
        assert resolve_area_scope(identity) == frozenset({"OM"})

    def test_ma_group_vocabulary_contains_all_four_mas(self):
        assert set(MA_AREA_GROUPS.keys()) == {"MA1", "MA2", "MA3", "MA4"}


class TestResolveAreaScopePertaminaByAll:
    def test_pertamina_engineer_with_all_scope_gets_full_area_codes(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="ALL")
        assert resolve_area_scope(identity) == AREA_CODES
        assert resolve_area_scope(identity) == frozenset({"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"})

    def test_pertamina_engineer_with_all_scope_case_insensitive(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="all")
        assert resolve_area_scope(identity) == AREA_CODES

    def test_pertamina_engineer_with_all_scope_ignores_data_scope_value(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="ALL", data_scope_value="IGNORED")
        assert resolve_area_scope(identity) == AREA_CODES

    def test_pertamina_viewer_with_all_scope_gets_full_area_codes(self):
        identity = _identity("PERTAMINA_VIEWER", data_scope_type="ALL")
        assert resolve_area_scope(identity) == AREA_CODES

    def test_pertamina_engineer_is_never_unrestricted_even_with_all_scope(self):
        # CRITICAL NEGATIVE TEST:
        # resolve_area_scope must return AREA_CODES, NEVER None.
        # None grants unrestricted superuser status, bypassing area bounds.
        # AREA_CODES explicitly bounds access to valid LTSA physical areas.
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="ALL")
        scope = resolve_area_scope(identity)
        assert scope is not None
        assert isinstance(scope, frozenset)
        assert scope == AREA_CODES
        assert is_area_in_scope("NON_LTSA_AREA", scope) is False
        assert is_area_in_scope(None, scope) is False
        assert is_area_in_scope("HOC", scope) is True
        assert is_area_in_scope("HSC", scope) is True
        assert is_area_in_scope("S_PAKNING", scope) is True
        assert is_area_in_scope("HCC", scope) is True
        assert is_area_in_scope("OM", scope) is True
        assert is_area_in_scope("UTL", scope) is True


class TestResolveAreaScopeFailClosed:
    def test_pertamina_with_no_scope_recorded_gets_empty_scope_not_unrestricted(self):
        identity = _identity("PERTAMINA_ENGINEER")
        assert resolve_area_scope(identity) == frozenset()

    def test_unresolved_ma_value_gets_empty_scope_never_guessed(self):
        # Unresolved MA values (outside MA1..MA4) must fail closed.
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA5")
        assert resolve_area_scope(identity) == frozenset()

    def test_unknown_area_value_gets_empty_scope(self):
        identity = _identity("PERTAMINA_VIEWER", data_scope_type="AREA", data_scope_value="NOT_A_REAL_AREA")
        assert resolve_area_scope(identity) == frozenset()

    def test_unknown_scope_type_gets_empty_scope(self):
        identity = _identity("PERTAMINA_ENGINEER", data_scope_type="DEPARTMENT", data_scope_value="REFINERY")
        assert resolve_area_scope(identity) == frozenset()


class TestIsAreaInScope:
    def test_unrestricted_scope_allows_anything(self):
        assert is_area_in_scope("HOC", None) is True
        assert is_area_in_scope(None, None) is True

    def test_restricted_scope_checks_membership(self):
        scope = frozenset({"HOC"})
        assert is_area_in_scope("HOC", scope) is True
        assert is_area_in_scope("HSC", scope) is False

    def test_record_with_no_area_never_in_scope_for_a_restricted_identity(self):
        assert is_area_in_scope(None, frozenset({"HOC"})) is False


class TestFilterRecordsByScope:
    def test_unrestricted_returns_every_record_unfiltered(self):
        records = [{"area": "HOC"}, {"area": "UTL"}]
        assert filter_records_by_scope(records, None) == records

    def test_restricted_drops_out_of_scope_records(self):
        records = [{"tag_number": "1", "area": "HOC"}, {"tag_number": "2", "area": "UTL"}]
        result = filter_records_by_scope(records, frozenset({"HOC"}))
        assert [r["tag_number"] for r in result] == ["1"]

    def test_ma2_scope_keeps_all_three_grouped_areas(self):
        records = [
            {"tag_number": "1", "area": "HSC"},
            {"tag_number": "2", "area": "S_PAKNING"},
            {"tag_number": "3", "area": "HCC"},
            {"tag_number": "4", "area": "HOC"},
        ]
        result = filter_records_by_scope(records, frozenset({"HSC", "S_PAKNING", "HCC"}))
        assert {r["tag_number"] for r in result} == {"1", "2", "3"}

    def test_empty_scope_drops_every_record(self):
        records = [{"tag_number": "1", "area": "HOC"}]
        assert filter_records_by_scope(records, frozenset()) == []

    def test_all_scope_keeps_all_six_ltsa_areas_and_drops_non_ltsa(self):
        records = [
            {"tag_number": "1", "area": "HOC"},
            {"tag_number": "2", "area": "HSC"},
            {"tag_number": "3", "area": "S_PAKNING"},
            {"tag_number": "4", "area": "HCC"},
            {"tag_number": "5", "area": "OM"},
            {"tag_number": "6", "area": "UTL"},
            {"tag_number": "7", "area": "UNKNOWN_OFFSHORE"},
        ]
        result = filter_records_by_scope(records, AREA_CODES)
        assert {r["tag_number"] for r in result} == {"1", "2", "3", "4", "5", "6"}

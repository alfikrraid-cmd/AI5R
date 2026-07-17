"""Behavioral tests for MaintenanceRelationshipResolver (UMC-001 Stage 5,
per MWO-LTSA-054 WP-001). Mirrors test_pump_relationship_resolver.py /
test_seal_relationship_resolver.py, extended for Maintenance's two
relationships (§3 of MWO-LTSA-054 WP-000): the four-registry polymorphic
`asset_code`/`asset_type` dispatch, and the optional, non-error
`work_order_code` link from Maintenance History.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/MAINTENANCE-FACTORY-PACK/TEST/
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_AI5R_SDK_PATH = Path(__file__).resolve().parents[4] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext  # noqa: E402
from FACTORY.RESOLUTION.relationship_resolver import RelationshipResolution  # noqa: E402

from maintenance_relationship_resolver import MaintenanceRelationshipResolver  # noqa: E402


def _context() -> ManufacturingContext:
    return ManufacturingContext(build_id="BUILD-MTN-1", product="LTSA-BRAIN", version="1.0")


def test_resolves_asset_code_against_pump_registry():
    resolver = MaintenanceRelationshipResolver(known_pumps=[{"tag_number": "P-101"}])

    result = resolver.resolve(
        "WORK_ORDER", {"asset_code": "P-101", "asset_type": "PUMP"}, _context()
    )

    assert isinstance(result, RelationshipResolution)
    assert result.resolved == {"asset_code": "P-101"}
    assert result.unresolved == []


def test_resolves_asset_code_against_seal_registry():
    resolver = MaintenanceRelationshipResolver(known_seals=[{"seal_code": "SC-9"}])

    result = resolver.resolve(
        "WORK_ORDER", {"asset_code": "SC-9", "asset_type": "SEAL"}, _context()
    )

    assert result.resolved == {"asset_code": "SC-9"}
    assert result.unresolved == []


def test_resolves_asset_code_against_asset_registry():
    resolver = MaintenanceRelationshipResolver(known_assets=[{"asset_code": "AST-1"}])

    result = resolver.resolve(
        "WORK_ORDER", {"asset_code": "AST-1", "asset_type": "ASSET"}, _context()
    )

    assert result.resolved == {"asset_code": "AST-1"}


def test_resolves_asset_code_against_soot_blower_registry():
    resolver = MaintenanceRelationshipResolver(known_soot_blowers=[{"soot_blower_code": "SB-1"}])

    result = resolver.resolve(
        "WORK_ORDER", {"asset_code": "SB-1", "asset_type": "SOOT_BLOWER"}, _context()
    )

    assert result.resolved == {"asset_code": "SB-1"}


def test_reports_unresolved_for_unknown_asset_code():
    resolver = MaintenanceRelationshipResolver(known_pumps=[{"tag_number": "P-101"}])

    result = resolver.resolve(
        "WORK_ORDER", {"asset_code": "P-999", "asset_type": "PUMP"}, _context()
    )

    assert result.resolved == {}
    assert result.unresolved == ["asset_code"]


def test_reports_unresolved_for_an_unknown_asset_type():
    resolver = MaintenanceRelationshipResolver()

    result = resolver.resolve(
        "WORK_ORDER", {"asset_code": "X-1", "asset_type": "UNKNOWN_TYPE"}, _context()
    )

    assert result.unresolved == ["asset_code"]


def test_resolves_a_known_work_order_code_for_maintenance_history():
    resolver = MaintenanceRelationshipResolver(known_work_orders=[{"work_order_code": "WO-101"}])

    result = resolver.resolve(
        "MAINTENANCE_RECORD", {"work_order_code": "WO-101"}, _context()
    )

    assert result.resolved == {"work_order_code": "WO-101"}
    assert result.unresolved == []


def test_reports_unresolved_not_error_for_an_absent_work_order_code():
    """Per MWO-LTSA-054 WP-000 §3: work_order_code is deliberately optional --
    an unresolved result is a legitimate outcome, not an error."""
    resolver = MaintenanceRelationshipResolver(known_work_orders=[{"work_order_code": "WO-101"}])

    result = resolver.resolve(
        "MAINTENANCE_RECORD", {"work_order_code": "WO-999"}, _context()
    )

    assert result.resolved == {}
    assert result.unresolved == ["work_order_code"]


def test_defaults_to_empty_registries():
    resolver = MaintenanceRelationshipResolver()

    result = resolver.resolve(
        "WORK_ORDER", {"asset_code": "P-101", "asset_type": "PUMP"}, _context()
    )

    assert result.resolved == {}
    assert result.unresolved == ["asset_code"]

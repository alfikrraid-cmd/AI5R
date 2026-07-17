"""Behavioral tests for MaintenanceIdentityResolver (UMC-001 Stage 4, per
MWO-LTSA-054 WP-001). Mirrors test_pump_identity_resolver.py /
test_seal_identity_resolver.py, extended for Maintenance's two canonical
objects (Work Order, Maintenance History) per MWO-LTSA-054 WP-000 Finding 1.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/MAINTENANCE-FACTORY-PACK/TEST/
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_AI5R_SDK_PATH = Path(__file__).resolve().parents[4] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

import pytest  # noqa: E402

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext  # noqa: E402
from FACTORY.RESOLUTION.identity_resolver import IdentityResolution  # noqa: E402

from maintenance_identity_resolver import MaintenanceIdentityResolver  # noqa: E402


def _context() -> ManufacturingContext:
    return ManufacturingContext(build_id="BUILD-MTN-1", product="LTSA-BRAIN", version="1.0")


def test_matches_an_existing_work_order_by_work_order_code():
    resolver = MaintenanceIdentityResolver(
        known_work_orders=[{"work_order_code": "WO-101"}]
    )

    result = resolver.resolve("WORK_ORDER", {"work_order_code": "WO-101"}, _context())

    assert isinstance(result, IdentityResolution)
    assert result.matched is True
    assert result.canonical_id == "WO-101"
    assert result.confidence == 1.0


def test_does_not_match_an_unknown_work_order_code():
    resolver = MaintenanceIdentityResolver(known_work_orders=[{"work_order_code": "WO-101"}])

    result = resolver.resolve("WORK_ORDER", {"work_order_code": "WO-999"}, _context())

    assert result.matched is False
    assert result.canonical_id is None
    assert result.confidence is None


def test_matches_an_existing_maintenance_record_by_maintenance_record_code():
    resolver = MaintenanceIdentityResolver(
        known_maintenance_records=[{"maintenance_record_code": "MR-001"}]
    )

    result = resolver.resolve(
        "MAINTENANCE_RECORD", {"maintenance_record_code": "MR-001"}, _context()
    )

    assert result.matched is True
    assert result.canonical_id == "MR-001"
    assert result.confidence == 1.0


def test_does_not_match_an_unknown_maintenance_record_code():
    resolver = MaintenanceIdentityResolver(
        known_maintenance_records=[{"maintenance_record_code": "MR-001"}]
    )

    result = resolver.resolve(
        "MAINTENANCE_RECORD", {"maintenance_record_code": "MR-999"}, _context()
    )

    assert result.matched is False


def test_defaults_to_no_known_records():
    resolver = MaintenanceIdentityResolver()

    assert resolver.resolve("WORK_ORDER", {"work_order_code": "WO-101"}, _context()).matched is False
    assert (
        resolver.resolve(
            "MAINTENANCE_RECORD", {"maintenance_record_code": "MR-001"}, _context()
        ).matched
        is False
    )


def test_rejects_an_unsupported_object_type():
    resolver = MaintenanceIdentityResolver()

    with pytest.raises(ValueError):
        resolver.resolve("PUMP", {"tag_number": "P-101"}, _context())

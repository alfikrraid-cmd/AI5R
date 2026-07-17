"""Behavioral tests for MaintenanceManufacturingStation. Mirrors
test_pump_manufacturing_station.py / test_seal_manufacturing_station.py,
extended to dispatch on payload["definition"]["object_type"] between
Work Order and Maintenance History (MWO-LTSA-054 WP-000 Finding 1: two
canonical objects, one station, per Chief Direction's single-file deliverable
list).

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

from FACTORY.CORE.exceptions import ManufacturingValidationError  # noqa: E402
from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext  # noqa: E402
from FACTORY.RESOLUTION.identity_resolver import IdentityResolution, IdentityResolver  # noqa: E402
from FACTORY.RESOLUTION.relationship_resolver import (  # noqa: E402
    RelationshipResolution,
    RelationshipResolver,
)

from maintenance_manufacturing_station import MaintenanceManufacturingStation  # noqa: E402


class StubIdentityResolver(IdentityResolver):
    def __init__(self, matched: bool):
        self.matched = matched

    def resolve(self, object_type, candidate_key, context):
        canonical = next(iter(candidate_key.values()), None)
        return IdentityResolution(
            matched=self.matched,
            canonical_id=canonical if self.matched else None,
            confidence=1.0 if self.matched else None,
        )


class StubRelationshipResolver(RelationshipResolver):
    def resolve(self, object_type, candidate_relationships, context):
        return RelationshipResolution(resolved={"asset_code": "P-101"}, unresolved=[])


def _payload(object_type: str, record: dict, context: ManufacturingContext | None = None) -> dict:
    definition_key = "work_order" if object_type == "WORK_ORDER" else "maintenance_record"
    return {
        "product": "MAINTENANCE",
        "definition": {"object_type": object_type, definition_key: record},
        "status": "COMPILED",
        "context": context,
    }


def test_manufactures_a_new_work_order_without_any_resolvers():
    station = MaintenanceManufacturingStation()

    result = station.run(
        _payload("WORK_ORDER", {"work_order_code": "WO-101", "description": "Inspect seal"})
    )

    assert result["status"] == "MANUFACTURED"
    assert result["manufactured_object"]["type"] == "WORK_ORDER"
    assert result["manufactured_object"]["payload"]["work_order_code"] == "WO-101"
    assert result["object_id"]


def test_manufactures_a_new_maintenance_record_without_any_resolvers():
    station = MaintenanceManufacturingStation()

    result = station.run(
        _payload(
            "MAINTENANCE_RECORD",
            {"maintenance_record_code": "MR-001", "action_taken": "Replaced seal"},
        )
    )

    assert result["status"] == "MANUFACTURED"
    assert result["manufactured_object"]["type"] == "MAINTENANCE_RECORD"
    assert result["manufactured_object"]["payload"]["maintenance_record_code"] == "MR-001"


def test_requires_a_work_order_code():
    station = MaintenanceManufacturingStation()

    with pytest.raises(ManufacturingValidationError):
        station.run(_payload("WORK_ORDER", {"description": "Inspect seal"}))


def test_requires_a_maintenance_record_code():
    station = MaintenanceManufacturingStation()

    with pytest.raises(ManufacturingValidationError):
        station.run(_payload("MAINTENANCE_RECORD", {"action_taken": "Replaced seal"}))


def test_rejects_an_unsupported_object_type():
    station = MaintenanceManufacturingStation()

    with pytest.raises(ValueError):
        station.run(_payload("PUMP", {"tag_number": "P-101"}))


def test_wires_identity_and_relationship_resolution_via_context():
    context = ManufacturingContext(
        build_id="BUILD-MTN-1",
        product="LTSA-BRAIN",
        version="1.0",
        metadata={
            "identity_resolver": StubIdentityResolver(matched=False),
            "relationship_resolver": StubRelationshipResolver(),
        },
    )
    station = MaintenanceManufacturingStation()

    result = station.run(
        _payload(
            "WORK_ORDER",
            {"work_order_code": "WO-101", "description": "Inspect", "asset_code": "P-101", "asset_type": "PUMP"},
            context=context,
        )
    )

    assert result["status"] == "MANUFACTURED"
    metadata = result["manufactured_object"]["metadata"]
    assert metadata["identity_resolution"]["matched"] is False
    assert metadata["relationship_resolution"]["resolved"] == {"asset_code": "P-101"}


def test_rejects_manufacturing_a_work_order_that_already_exists():
    context = ManufacturingContext(
        build_id="BUILD-MTN-1",
        product="LTSA-BRAIN",
        version="1.0",
        metadata={"identity_resolver": StubIdentityResolver(matched=True)},
    )
    station = MaintenanceManufacturingStation()

    result = station.run(
        _payload("WORK_ORDER", {"work_order_code": "WO-101", "description": "Inspect"}, context=context)
    )

    assert result["status"] == "WORK_ORDER_ALREADY_EXISTS"
    assert "manufactured_object" not in result


def test_rejects_manufacturing_a_maintenance_record_that_already_exists():
    context = ManufacturingContext(
        build_id="BUILD-MTN-1",
        product="LTSA-BRAIN",
        version="1.0",
        metadata={"identity_resolver": StubIdentityResolver(matched=True)},
    )
    station = MaintenanceManufacturingStation()

    result = station.run(
        _payload(
            "MAINTENANCE_RECORD",
            {"maintenance_record_code": "MR-001", "action_taken": "Replaced seal"},
            context=context,
        )
    )

    assert result["status"] == "MAINTENANCE_RECORD_ALREADY_EXISTS"
    assert "manufactured_object" not in result


def test_run_is_pipeline_compatible_and_returns_a_status_key():
    station = MaintenanceManufacturingStation()

    result = station.run(_payload("WORK_ORDER", {"work_order_code": "WO-101", "description": "Inspect"}))

    assert isinstance(result, dict)
    assert "status" in result

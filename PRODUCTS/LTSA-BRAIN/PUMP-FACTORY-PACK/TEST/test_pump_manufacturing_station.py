"""Behavioral tests for PumpManufacturingStation.

Subclasses FACTORY.CORE.manufacturing_station.BaseManufacturingStation
unchanged (Chief Architect directive: Manufacturing Station is a Factory
concept, reuse the existing UMC-001 lifecycle, do not introduce a second
execution model). Exposes `.run(payload) -> dict`, the station shape
FACTORY.FOUNDATION.manufacturing_pipeline.ManufacturingPipeline actually
calls (UMR-001 Section 5), and wires UMC-001 Stage 4 (Identity Resolution)
and Stage 5 (Relationship Resolution) ahead of the inherited
BaseManufacturingStation.manufacture() call that fulfils Stage 3/6-8.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/PUMP-FACTORY-PACK/TEST/
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

from pump_manufacturing_station import PumpManufacturingStation  # noqa: E402


class StubIdentityResolver(IdentityResolver):
    def __init__(self, matched: bool):
        self.matched = matched

    def resolve(self, object_type, candidate_key, context):
        return IdentityResolution(
            matched=self.matched,
            canonical_id="P-101" if self.matched else None,
            confidence=1.0 if self.matched else None,
        )


class StubRelationshipResolver(RelationshipResolver):
    def resolve(self, object_type, candidate_relationships, context):
        return RelationshipResolution(resolved={"seal_type": "SC-9"}, unresolved=[])


def _payload(pump: dict, context: ManufacturingContext | None = None) -> dict:
    return {
        "product": "PUMP",
        "definition": {"pump": pump},
        "status": "COMPILED",
        "context": context,
    }


def test_manufactures_a_new_pump_without_any_resolvers():
    station = PumpManufacturingStation()

    result = station.run(_payload({"tag_number": "P-101", "area": "AREA-1"}))

    assert result["status"] == "MANUFACTURED"
    assert result["manufactured_object"]["type"] == "PUMP"
    assert result["manufactured_object"]["payload"]["tag_number"] == "P-101"
    assert result["object_id"]


def test_requires_a_tag_number():
    station = PumpManufacturingStation()

    with pytest.raises(ManufacturingValidationError):
        station.run(_payload({"area": "AREA-1"}))


def test_wires_identity_and_relationship_resolution_via_context():
    context = ManufacturingContext(
        build_id="BUILD-PUMP-1",
        product="LTSA-BRAIN",
        version="1.0",
        metadata={
            "identity_resolver": StubIdentityResolver(matched=False),
            "relationship_resolver": StubRelationshipResolver(),
        },
    )
    station = PumpManufacturingStation()

    result = station.run(
        _payload({"tag_number": "P-101", "seal_type": "Type 21"}, context=context)
    )

    assert result["status"] == "MANUFACTURED"
    metadata = result["manufactured_object"]["metadata"]
    assert metadata["identity_resolution"]["matched"] is False
    assert metadata["relationship_resolution"]["resolved"] == {"seal_type": "SC-9"}


def test_rejects_manufacturing_a_pump_that_already_exists():
    context = ManufacturingContext(
        build_id="BUILD-PUMP-1",
        product="LTSA-BRAIN",
        version="1.0",
        metadata={"identity_resolver": StubIdentityResolver(matched=True)},
    )
    station = PumpManufacturingStation()

    result = station.run(_payload({"tag_number": "P-101"}, context=context))

    assert result["status"] == "PUMP_ALREADY_EXISTS"
    assert "manufactured_object" not in result


def test_run_is_pipeline_compatible_and_returns_a_status_key():
    station = PumpManufacturingStation()

    result = station.run(_payload({"tag_number": "P-101"}))

    assert isinstance(result, dict)
    assert "status" in result

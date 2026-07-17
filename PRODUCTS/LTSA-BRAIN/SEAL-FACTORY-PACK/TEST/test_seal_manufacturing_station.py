"""Behavioral tests for SealManufacturingStation. Mirrors
test_pump_manufacturing_station.py.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/SEAL-FACTORY-PACK/TEST/
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

from seal_manufacturing_station import SealManufacturingStation  # noqa: E402


class StubIdentityResolver(IdentityResolver):
    def __init__(self, matched: bool):
        self.matched = matched

    def resolve(self, object_type, candidate_key, context):
        return IdentityResolution(
            matched=self.matched,
            canonical_id="SC-9" if self.matched else None,
            confidence=1.0 if self.matched else None,
        )


class StubRelationshipResolver(RelationshipResolver):
    def resolve(self, object_type, candidate_relationships, context):
        return RelationshipResolution(resolved={"compatible_seal_name": "SC-4"}, unresolved=[])


def _payload(seal: dict, context: ManufacturingContext | None = None) -> dict:
    return {
        "product": "SEAL",
        "definition": {"seal": seal},
        "status": "COMPILED",
        "context": context,
    }


def test_manufactures_a_new_seal_without_any_resolvers():
    station = SealManufacturingStation()

    result = station.run(_payload({"seal_code": "SC-9", "seal_name": "Type 21"}))

    assert result["status"] == "MANUFACTURED"
    assert result["manufactured_object"]["type"] == "SEAL"
    assert result["manufactured_object"]["payload"]["seal_code"] == "SC-9"
    assert result["object_id"]


def test_requires_a_seal_code():
    station = SealManufacturingStation()

    with pytest.raises(ManufacturingValidationError):
        station.run(_payload({"seal_name": "Type 21"}))


def test_wires_identity_and_relationship_resolution_via_context():
    context = ManufacturingContext(
        build_id="BUILD-SEAL-1",
        product="LTSA-BRAIN",
        version="1.0",
        metadata={
            "identity_resolver": StubIdentityResolver(matched=False),
            "relationship_resolver": StubRelationshipResolver(),
        },
    )
    station = SealManufacturingStation()

    result = station.run(
        _payload(
            {"seal_code": "SC-9", "compatible_seal_name": "JC-100"}, context=context
        )
    )

    assert result["status"] == "MANUFACTURED"
    metadata = result["manufactured_object"]["metadata"]
    assert metadata["identity_resolution"]["matched"] is False
    assert metadata["relationship_resolution"]["resolved"] == {"compatible_seal_name": "SC-4"}


def test_rejects_manufacturing_a_seal_that_already_exists():
    context = ManufacturingContext(
        build_id="BUILD-SEAL-1",
        product="LTSA-BRAIN",
        version="1.0",
        metadata={"identity_resolver": StubIdentityResolver(matched=True)},
    )
    station = SealManufacturingStation()

    result = station.run(_payload({"seal_code": "SC-9"}, context=context))

    assert result["status"] == "SEAL_ALREADY_EXISTS"
    assert "manufactured_object" not in result


def test_run_is_pipeline_compatible_and_returns_a_status_key():
    station = SealManufacturingStation()

    result = station.run(_payload({"seal_code": "SC-9"}))

    assert isinstance(result, dict)
    assert "status" in result

"""Behavioral tests for PumpRelationshipResolver (UMC-001 Stage 5, first
concrete implementer per MWO-LTSA-048 Section 6 / MWO-LTSA-050 WP-000).

Resolves a Pump's free-text `seal_type` against `seal_registry.seal_name`,
returning the canonical `seal_code` -- the cross-reference already load-
bearing via `seal_pump_compatibility` (MWO-LTSA-030).

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/PUMP-FACTORY-PACK/TEST/
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

from pump_relationship_resolver import PumpRelationshipResolver  # noqa: E402


def _context() -> ManufacturingContext:
    return ManufacturingContext(build_id="BUILD-PUMP-1", product="LTSA-BRAIN", version="1.0")


_SEAL_REGISTRY = [
    {"seal_code": "SC-9", "seal_name": "Type 21"},
    {"seal_code": "SC-4", "seal_name": "Type 1"},
]


def test_resolves_known_seal_type_to_seal_code():
    resolver = PumpRelationshipResolver(seal_registry=_SEAL_REGISTRY)

    result = resolver.resolve("PUMP", {"seal_type": "Type 21"}, _context())

    assert isinstance(result, RelationshipResolution)
    assert result.resolved == {"seal_type": "SC-9"}
    assert result.unresolved == []


def test_reports_unresolved_for_unknown_seal_type():
    resolver = PumpRelationshipResolver(seal_registry=_SEAL_REGISTRY)

    result = resolver.resolve("PUMP", {"seal_type": "Type 99"}, _context())

    assert result.resolved == {}
    assert result.unresolved == ["seal_type"]


def test_reports_unresolved_for_an_unsupported_relationship_key():
    resolver = PumpRelationshipResolver(seal_registry=_SEAL_REGISTRY)

    result = resolver.resolve("PUMP", {"impeller_type": "Closed"}, _context())

    assert result.resolved == {}
    assert result.unresolved == ["impeller_type"]


def test_defaults_to_empty_seal_registry():
    resolver = PumpRelationshipResolver()

    result = resolver.resolve("PUMP", {"seal_type": "Type 21"}, _context())

    assert result.resolved == {}
    assert result.unresolved == ["seal_type"]

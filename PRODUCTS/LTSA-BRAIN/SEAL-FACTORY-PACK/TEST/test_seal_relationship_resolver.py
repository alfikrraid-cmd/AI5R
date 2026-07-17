"""Behavioral tests for SealRelationshipResolver (UMC-001 Stage 5, per
MWO-LTSA-052 WP-001). Mirrors test_pump_relationship_resolver.py.

Resolves a Seal's free-text `compatible_seal_name` against
`seal_registry.seal_name`, returning the canonical `seal_code` -- the
cross-reference `seal_interchange_compatibility` already requires
(MWO-LTSA-030).

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/SEAL-FACTORY-PACK/TEST/
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

from seal_relationship_resolver import SealRelationshipResolver  # noqa: E402


def _context() -> ManufacturingContext:
    return ManufacturingContext(build_id="BUILD-SEAL-1", product="LTSA-BRAIN", version="1.0")


_SEAL_REGISTRY = [
    {"seal_code": "SC-9", "seal_name": "JC-100"},
    {"seal_code": "SC-4", "seal_name": "JC-102"},
]


def test_resolves_known_compatible_seal_name_to_seal_code():
    resolver = SealRelationshipResolver(seal_registry=_SEAL_REGISTRY)

    result = resolver.resolve("SEAL", {"compatible_seal_name": "JC-100"}, _context())

    assert isinstance(result, RelationshipResolution)
    assert result.resolved == {"compatible_seal_name": "SC-9"}
    assert result.unresolved == []


def test_reports_unresolved_for_unknown_compatible_seal_name():
    resolver = SealRelationshipResolver(seal_registry=_SEAL_REGISTRY)

    result = resolver.resolve("SEAL", {"compatible_seal_name": "Unknown-999"}, _context())

    assert result.resolved == {}
    assert result.unresolved == ["compatible_seal_name"]


def test_reports_unresolved_for_an_unsupported_relationship_key():
    resolver = SealRelationshipResolver(seal_registry=_SEAL_REGISTRY)

    result = resolver.resolve("SEAL", {"pump_tag_number": "P-101"}, _context())

    assert result.resolved == {}
    assert result.unresolved == ["pump_tag_number"]


def test_defaults_to_empty_seal_registry():
    resolver = SealRelationshipResolver()

    result = resolver.resolve("SEAL", {"compatible_seal_name": "JC-100"}, _context())

    assert result.resolved == {}
    assert result.unresolved == ["compatible_seal_name"]

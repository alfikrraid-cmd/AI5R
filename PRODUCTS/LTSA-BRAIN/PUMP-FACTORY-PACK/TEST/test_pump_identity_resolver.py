"""Behavioral tests for PumpIdentityResolver (UMC-001 Stage 4, first concrete
implementer per MWO-LTSA-048 Section 6 / MWO-LTSA-050 WP-000).

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

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext  # noqa: E402
from FACTORY.RESOLUTION.identity_resolver import IdentityResolution  # noqa: E402

from pump_identity_resolver import PumpIdentityResolver  # noqa: E402


def _context() -> ManufacturingContext:
    return ManufacturingContext(build_id="BUILD-PUMP-1", product="LTSA-BRAIN", version="1.0")


def test_matches_an_existing_pump_by_tag_number():
    resolver = PumpIdentityResolver(known_pumps=[{"tag_number": "P-101", "area": "AREA-1"}])

    result = resolver.resolve("PUMP", {"tag_number": "P-101"}, _context())

    assert isinstance(result, IdentityResolution)
    assert result.matched is True
    assert result.canonical_id == "P-101"
    assert result.confidence == 1.0


def test_does_not_match_an_unknown_tag_number():
    resolver = PumpIdentityResolver(known_pumps=[{"tag_number": "P-101"}])

    result = resolver.resolve("PUMP", {"tag_number": "P-999"}, _context())

    assert result.matched is False
    assert result.canonical_id is None
    assert result.confidence is None


def test_defaults_to_no_known_pumps():
    resolver = PumpIdentityResolver()

    result = resolver.resolve("PUMP", {"tag_number": "P-101"}, _context())

    assert result.matched is False


def test_rejects_a_non_pump_object_type():
    resolver = PumpIdentityResolver(known_pumps=[{"tag_number": "P-101"}])

    with pytest.raises(ValueError):
        resolver.resolve("SEAL", {"tag_number": "P-101"}, _context())

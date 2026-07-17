"""Behavioral tests for SealIdentityResolver (UMC-001 Stage 4, per
MWO-LTSA-052 WP-001). Mirrors test_pump_identity_resolver.py.

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

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext  # noqa: E402
from FACTORY.RESOLUTION.identity_resolver import IdentityResolution  # noqa: E402

from seal_identity_resolver import SealIdentityResolver  # noqa: E402


def _context() -> ManufacturingContext:
    return ManufacturingContext(build_id="BUILD-SEAL-1", product="LTSA-BRAIN", version="1.0")


def test_matches_an_existing_seal_by_seal_code():
    resolver = SealIdentityResolver(known_seals=[{"seal_code": "SC-9", "seal_name": "Type 21"}])

    result = resolver.resolve("SEAL", {"seal_code": "SC-9"}, _context())

    assert isinstance(result, IdentityResolution)
    assert result.matched is True
    assert result.canonical_id == "SC-9"
    assert result.confidence == 1.0


def test_does_not_match_an_unknown_seal_code():
    resolver = SealIdentityResolver(known_seals=[{"seal_code": "SC-9"}])

    result = resolver.resolve("SEAL", {"seal_code": "SC-999"}, _context())

    assert result.matched is False
    assert result.canonical_id is None
    assert result.confidence is None


def test_defaults_to_no_known_seals():
    resolver = SealIdentityResolver()

    result = resolver.resolve("SEAL", {"seal_code": "SC-9"}, _context())

    assert result.matched is False


def test_rejects_a_non_seal_object_type():
    resolver = SealIdentityResolver(known_seals=[{"seal_code": "SC-9"}])

    with pytest.raises(ValueError):
        resolver.resolve("PUMP", {"seal_code": "SC-9"}, _context())

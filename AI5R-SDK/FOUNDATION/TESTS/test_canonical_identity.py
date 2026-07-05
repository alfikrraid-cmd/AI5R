import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_identity import (
    CanonicalIdentityGenerator,
)


def setup_function():
    CanonicalIdentityGenerator.reset()


def test_generate_identity():
    identity = CanonicalIdentityGenerator.generate("KNW")

    assert identity.prefix == "KNW"
    assert identity.value.startswith("AI5R-KNW-")


def test_identity_is_unique():
    a = CanonicalIdentityGenerator.generate("KNW")
    b = CanonicalIdentityGenerator.generate("KNW")

    assert a.value != b.value


def test_counter_increases():
    CanonicalIdentityGenerator.generate("EVT")
    CanonicalIdentityGenerator.generate("EVT")
    CanonicalIdentityGenerator.generate("EVT")

    assert CanonicalIdentityGenerator.current_counter("EVT") == 3


def test_different_prefixes_have_independent_counters():
    CanonicalIdentityGenerator.generate("KNW")
    CanonicalIdentityGenerator.generate("EVT")
    CanonicalIdentityGenerator.generate("OBJ")

    assert CanonicalIdentityGenerator.current_counter("KNW") == 1
    assert CanonicalIdentityGenerator.current_counter("EVT") == 1
    assert CanonicalIdentityGenerator.current_counter("OBJ") == 1


def test_reset():
    CanonicalIdentityGenerator.generate("KNW")

    CanonicalIdentityGenerator.reset()

    assert CanonicalIdentityGenerator.current_counter("KNW") == 0

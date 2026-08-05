"""
MWO-ARCH011-EP01 -- FOUNDATION's relationship to ARCH-011's BASE family.
"""

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_exists():
    assert README.exists()


def test_readme_references_arch_011():
    text = README.read_text()
    assert "ARCH-011" in text


def test_readme_states_base_family_relationship():
    text = README.read_text()
    assert "BASE" in text


def test_readme_lists_canonical_components():
    text = README.read_text()
    for component in [
        "CanonicalObject",
        "CanonicalEvent",
        "CanonicalIdentity",
        "CanonicalRegistry",
        "CanonicalRuntime",
    ]:
        assert component in text

"""
MWO-RAE-000E -- verifies the evidence package's barrel exports exactly
the seven canonical Repository Evidence Objects, mirroring
design-system/index.js's own "exact export set" test discipline.
"""

from REPOSITORY_ARCHAEOLOGY import evidence


def test_exports_all_seven_evidence_objects():
    expected = {
        "ParsedModule",
        "ParsedClass",
        "ParsedFunction",
        "ParsedImport",
        "ParsedComment",
        "ParsedDocstring",
        "ParsedDependency",
    }

    for name in expected:
        assert hasattr(evidence, name), f"evidence package does not export {name}"


def test_exports_nothing_beyond_the_seven_canonical_objects():
    expected = {
        "ParsedModule",
        "ParsedClass",
        "ParsedFunction",
        "ParsedImport",
        "ParsedComment",
        "ParsedDocstring",
        "ParsedDependency",
    }

    assert set(evidence.__all__) == expected

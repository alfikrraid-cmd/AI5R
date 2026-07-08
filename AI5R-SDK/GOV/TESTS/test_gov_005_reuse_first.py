from pathlib import Path


DOC = Path(
    "AI5R-SDK/GOV/GOV-005-REUSE-FIRST.md"
)


def test_document_exists():
    assert DOC.exists()


def test_contains_canonical_law():
    text = DOC.read_text()

    assert "There shall be only one canonical implementation of every concept" in text


def test_contains_architecture_gate():
    text = DOC.read_text()

    assert "Does a Canonical Engine already exist?" in text
    assert "Can Recipe solve the problem?" in text


def test_contains_engine_vs_definition():
    text = DOC.read_text()

    assert "Canonical Engine" in text
    assert "Definition" in text
    assert "Runtime" in text


def test_contains_principle():
    text = DOC.read_text()

    assert "AI5R prefers extending Definitions over creating Engines." in text

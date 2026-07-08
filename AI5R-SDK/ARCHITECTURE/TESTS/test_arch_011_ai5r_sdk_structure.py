from pathlib import Path


DOC = Path("AI5R-SDK/ARCHITECTURE/DOCS/ARCH-011-AI5R-SDK-STRUCTURE.md")


def test_arch_011_document_exists():
    assert DOC.exists()


def test_arch_011_locks_concept_not_folder_rule():
    text = DOC.read_text()

    assert "A concept does not automatically become a folder" in text
    assert "Folders exist only when there is a real implementation responsibility" in text


def test_arch_011_contains_canonical_packages():
    text = DOC.read_text()

    assert "BASE" in text
    assert "GOV" in text
    assert "ARCHITECTURE" in text
    assert "ENTERPRISE" in text
    assert "MANUFACTURING" in text
    assert "INTELLIGENCE" in text
    assert "RUNTIME" in text
    assert "OSA" in text
    assert "FINANCE" in text
    assert "PRODUCTS" in text


def test_arch_011_locks_no_duplicate_engines():
    text = DOC.read_text()

    assert "Duplicate object engines" in text
    assert "Duplicate workflow engines" in text
    assert "Duplicate accounting engines" in text


def test_arch_011_contains_package_creation_rule():
    text = DOC.read_text()

    assert "Before creating a new top-level folder" in text
    assert "Has ARCH-000 been checked?" in text
    assert "If an existing package can own it, do not create a new folder" in text


def test_arch_011_locks_anti_sprawl_principle():
    text = DOC.read_text()

    assert "AI5R must prefer fewer stronger packages over many weak packages" in text
    assert "Concepts become documents first" in text

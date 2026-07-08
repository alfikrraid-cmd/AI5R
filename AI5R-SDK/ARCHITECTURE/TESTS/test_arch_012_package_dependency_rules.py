from pathlib import Path


DOC = Path("AI5R-SDK/ARCHITECTURE/DOCS/ARCH-012-PACKAGE-DEPENDENCY-RULES.md")


def test_arch_012_document_exists():
    assert DOC.exists()


def test_arch_012_locks_downward_dependency_rule():
    text = DOC.read_text()

    assert "Dependencies must flow downward" in text
    assert "Lower-level packages must not import higher-level packages" in text


def test_arch_012_contains_canonical_layers():
    text = DOC.read_text()

    assert "Layer 0: BASE" in text
    assert "Layer 3: ENTERPRISE" in text
    assert "Layer 4: MANUFACTURING" in text
    assert "Layer 7: FINANCE" in text
    assert "Layer 8: OSA" in text
    assert "Layer 9: PRODUCTS" in text


def test_arch_012_locks_base_as_root():
    text = DOC.read_text()

    assert "BASE must not import any AI5R package" in text
    assert "BASE is the root package" in text


def test_arch_012_forbids_product_imports_in_shared_packages():
    text = DOC.read_text()

    assert "No shared package may import PRODUCTS" in text
    assert "Manufacturing importing Products" in text
    assert "Finance importing Products" in text


def test_arch_012_contains_architecture_gate():
    text = DOC.read_text()

    assert "Before adding an import" in text
    assert "Does this create circular dependency?" in text
    assert "Can this be solved through a definition instead?" in text


def test_arch_012_locks_no_spider_web_principle():
    text = DOC.read_text()

    assert "AI5R must remain dependency-directed" in text
    assert "Dependencies must never become a spider web" in text

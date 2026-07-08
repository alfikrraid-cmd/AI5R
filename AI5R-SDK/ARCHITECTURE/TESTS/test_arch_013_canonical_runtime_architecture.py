from pathlib import Path

DOC = Path(
    "AI5R-SDK/ARCHITECTURE/DOCS/ARCH-013-CANONICAL-RUNTIME-ARCHITECTURE.md"
)

def test_document_exists():
    assert DOC.exists()

def test_single_runtime_engine():
    text = DOC.read_text()

    assert "There shall be only one Runtime Engine" in text
    assert "Many Runtime Profiles" in text

def test_forbidden_duplicate_runtimes():
    text = DOC.read_text()

    assert "ManufacturingRuntime" in text
    assert "FinanceRuntime" in text
    assert "EnterpriseRuntime" in text
    assert "AIRuntime" in text

def test_runtime_is_shared():
    text = DOC.read_text()

    assert "Runtime is shared." in text
    assert "Behavior is configured." in text

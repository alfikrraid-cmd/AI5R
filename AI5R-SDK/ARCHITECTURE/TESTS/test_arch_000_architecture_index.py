from pathlib import Path


DOC_PATH = Path("AI5R-SDK/ARCHITECTURE/DOCS/ARCH-000-ARCHITECTURE-INDEX.md")


def test_arch_000_document_exists():
    assert DOC_PATH.exists()


def test_arch_000_is_master_index():
    content = DOC_PATH.read_text()

    assert "master index of AI5R architecture decisions" in content
    assert "prevent duplicate architecture" in content
    assert "conflicting design decisions" in content


def test_arch_000_locks_no_duplicate_engines():
    content = DOC_PATH.read_text()

    assert "No duplicate engines" in content
    assert "Reuse existing modules whenever possible" in content


def test_arch_000_registers_current_architecture_documents():
    content = DOC_PATH.read_text()

    assert "ARCH-009" in content
    assert "ENT-003" in content
    assert "EAA-001A" in content
    assert "FIN-002" in content


def test_arch_000_contains_enterprise_os_principles():
    content = DOC_PATH.read_text()

    assert "AI5R is an Enterprise Operating System" in content
    assert "Every business object must use EnterpriseObject" in content
    assert "Every relationship must use Enterprise Knowledge Graph" in content
    assert "Every vertical must pass through Business Capability" in content
    assert "No vertical module may create journal entries directly" in content

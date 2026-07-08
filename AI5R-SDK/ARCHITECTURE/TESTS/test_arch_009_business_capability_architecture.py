from pathlib import Path


DOC_PATH = Path(
    "AI5R-SDK/ARCHITECTURE/DOCS/ARCH-009-BUSINESS-CAPABILITY-ARCHITECTURE.md"
)


def test_arch_009_document_exists():
    assert DOC_PATH.exists()


def test_arch_009_locks_capability_based_enterprise_os():
    content = DOC_PATH.read_text()

    assert "AI5R Enterprise OS is capability-based" in content
    assert "A company is built from business capabilities" in content


def test_arch_009_contains_enterprise_operating_flow():
    content = DOC_PATH.read_text()

    assert "EnterpriseObject" in content
    assert "EnterpriseEvent" in content
    assert "BusinessCapability" in content
    assert "EnterpriseDocument" in content
    assert "EnterpriseWorkflow" in content
    assert "EnterpriseTransaction" in content
    assert "EnterpriseAccounting" in content
    assert "ExecutiveIntelligence" in content


def test_arch_009_defines_required_capabilities():
    content = DOC_PATH.read_text()

    assert "SELL" in content
    assert "BUY" in content
    assert "PAY" in content
    assert "RECEIVE" in content
    assert "STORE" in content
    assert "MARKET" in content
    assert "RECRUIT" in content
    assert "TEACH" in content
    assert "ASSESS" in content


def test_arch_009_locks_no_vertical_bypass_rule():
    content = DOC_PATH.read_text()

    assert "No vertical module may bypass Business Capability" in content
    assert "The AI Organization Designer must not start from database tables" in content

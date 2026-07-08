from pathlib import Path


DOC = Path(
    "AI5R-SDK/GOV/GOV-000-DIGITAL-FACTORY.md"
)


def test_document_exists():
    assert DOC.exists()


def test_contains_vision():
    text = DOC.read_text()

    assert "AI5R is a Digital Factory" in text
    assert "manufacture any kind of digital product" in text


def test_contains_manufacturing_flow():
    text = DOC.read_text()

    assert "Manufacturing Order" in text
    assert "Digital Bill of Materials" in text
    assert "Manufacturing Stations" in text
    assert "Quality Assurance" in text


def test_contains_canonical_laws():
    text = DOC.read_text()

    assert "Everything digital is manufacturable" in text
    assert "Reuse before Create" in text
    assert "Governance before Implementation" in text


def test_contains_product_examples():
    text = DOC.read_text()

    assert "Enterprise Operating Systems" in text
    assert "AI Agents" in text
    assert "Websites" in text
    assert "Mobile Applications" in text
    assert "Automation" in text

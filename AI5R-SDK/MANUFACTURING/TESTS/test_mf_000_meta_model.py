from pathlib import Path

DOC = Path(
    "AI5R-SDK/MANUFACTURING/DOCS/MF-000-CANONICAL-MANUFACTURING-META-MODEL.md"
)

def test_document_exists():
    assert DOC.exists()

def test_contains_stack():
    text = DOC.read_text()

    assert "Digital Bill of Materials" in text
    assert "Manufacturing Recipe" in text
    assert "Manufacturing Order" in text
    assert "Manufacturing Line" in text
    assert "Manufacturing Station" in text

def test_contains_rule():
    text = DOC.read_text()

    assert "Factories manufacture Products." in text
    assert "Factories never manufacture Engines." in text

def test_contains_principle():
    text = DOC.read_text()

    assert "Everything Digital is Manufacturable." in text

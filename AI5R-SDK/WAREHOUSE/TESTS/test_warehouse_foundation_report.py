from pathlib import Path


def test_warehouse_foundation_report():
    path = Path("AI5R-SDK/WAREHOUSE/DOCS/WF-008-WAREHOUSE-FOUNDATION-REPORT.md")

    assert path.exists()

    content = path.read_text()

    assert "Warehouse Foundation completed" in content
    assert "Reality" in content
    assert "Warehouse" in content
    assert "Memory stores interpreted experience" in content
    assert "Knowledge stores validated and reusable understanding" in content

    print("WF-008 Warehouse Foundation Report OK")


if __name__ == "__main__":
    test_warehouse_foundation_report()

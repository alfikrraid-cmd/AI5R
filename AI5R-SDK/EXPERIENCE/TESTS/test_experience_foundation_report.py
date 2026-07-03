from pathlib import Path


def test_experience_foundation_report():
    path = Path("AI5R-SDK/EXPERIENCE/DOCS/EF-008-EXPERIENCE-FOUNDATION-REPORT.md")

    assert path.exists()

    content = path.read_text()

    assert "Experience Foundation completed" in content
    assert "Reality" in content
    assert "Warehouse" in content
    assert "Experience" in content
    assert "Experience is the first interpretation layer after Warehouse" in content
    assert "No Memory or Knowledge object should be created directly from Warehouse" in content

    print("EF-008 Experience Foundation Report OK")


if __name__ == "__main__":
    test_experience_foundation_report()

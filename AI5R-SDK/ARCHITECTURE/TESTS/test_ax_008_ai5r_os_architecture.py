from pathlib import Path


def test_ax_008_ai5r_os_architecture_exists():
    doc = (
        Path(__file__).resolve().parents[1]
        / "DOCS"
        / "AX-008-AI5R-OS-ARCHITECTURE.md"
    )

    assert doc.exists()

    content = doc.read_text(encoding="utf-8")

    assert "AI5R OS" in content
    assert "AI Operating System" in content
    assert "System Services" in content
    assert "Manufacturing Infrastructure" in content
    assert "Digital Process Runtime" in content
    assert "Digital Process" in content
    assert "Scheduler" in content
    assert "Event Bus" in content
    assert "Lifecycle Manager" in content
    assert "Process Manager" in content

from pathlib import Path


def test_ax_007_kernel_integration_freeze_exists():
    doc = (
        Path(__file__).resolve().parents[1]
        / "DOCS"
        / "AX-007-KERNEL-INTEGRATION-FREEZE.md"
    )

    assert doc.exists()

    content = doc.read_text(encoding="utf-8")

    assert "AI5R Kernel" in content
    assert "Manufacturing Pipeline" in content
    assert "Workflow Engine" in content
    assert "Station Dispatcher" in content
    assert "Station Registry" in content
    assert "Manufacturing Stations" in content
    assert "FROZEN" in content

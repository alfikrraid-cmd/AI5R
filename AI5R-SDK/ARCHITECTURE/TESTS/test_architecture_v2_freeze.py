from pathlib import Path


def test_architecture_v2_is_frozen():

    root = Path(__file__).resolve().parents[1]

    freeze = root / "DOCS" / "AX-009-ARCHITECTURE-V2-FREEZE.md"

    assert freeze.exists()

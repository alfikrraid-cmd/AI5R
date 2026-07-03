import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.universal_lifecycle import UniversalLifecycle


def test_lifecycle():

    lc = UniversalLifecycle()

    assert lc.status == "draft"

    lc.transition("active", "approved")

    lc.transition("completed", "execution finished")

    assert lc.status == "completed"

    assert len(lc.lifecycle_history) == 2

    print(lc.to_dict())

    print("AX-006 Universal Lifecycle OK")


if __name__ == "__main__":
    test_lifecycle()

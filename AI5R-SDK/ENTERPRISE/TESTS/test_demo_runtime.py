from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ENTERPRISE.DEMO import DemoRuntime


def test_demo_flow():
    demo = DemoRuntime()

    demo.spawn_employee("EMP-A")
    demo.assign_task("EMP-A", "TASK-1")
    demo.write_memory("EMP-A", {"event": "start"})
    demo.improve_skill("EMP-A", "negotiation")
    demo.evaluate("EMP-A")

    snapshot = demo.snapshot()

    assert snapshot["events"] == 5
    assert "EMP-A" in snapshot["state"]["employees"]
    assert len(snapshot["state"]["memory"]) == 1

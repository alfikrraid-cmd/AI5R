from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.SMOKE.runtime_smoke_test import RuntimeSmokeTest
from ARCHITECTURE.SMOKE.boot_simulation import BootSimulation


def test_full_runtime_smoke():
    sim = BootSimulation()
    test = RuntimeSmokeTest()

    steps = [
        ("boot", sim.boot_os),
        ("employee", sim.init_employee),
        ("memory", sim.init_memory),
        ("knowledge", sim.init_knowledge),
        ("agent", sim.spawn_agent),
        ("message", sim.send_message),
        ("skill", sim.update_skill),
        ("performance", sim.update_performance),
        ("shutdown", sim.shutdown),
        ("reload", sim.reload),
    ]

    result = test.run(steps)

    assert result.success is True

    state = sim.snapshot()

    assert all(state.values())

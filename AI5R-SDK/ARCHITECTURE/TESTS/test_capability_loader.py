import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import CapabilityLoader


def test_register_capability():
    loader = CapabilityLoader()

    capability = loader.register(
        capability_id="MEMORY",
        capability_type="CORE",
        implementation=object(),
    )

    assert capability.capability_id == "MEMORY"
    assert capability.enabled is True


def test_enable_disable():
    loader = CapabilityLoader()

    loader.register(
        "REASONING",
        "CORE",
        object(),
    )

    loader.disable("REASONING")
    assert loader.get("REASONING").enabled is False

    loader.enable("REASONING")
    assert loader.get("REASONING").enabled is True


def test_list_by_type():
    loader = CapabilityLoader()

    loader.register("MEMORY", "CORE", object())
    loader.register("EXECUTION", "CORE", object())
    loader.register("CRM", "PLUGIN", object())

    assert len(loader.list_by_type("CORE")) == 2
    assert len(loader.list_by_type("PLUGIN")) == 1


def test_summary():
    loader = CapabilityLoader()

    loader.register("A", "CORE", object())
    loader.register("B", "CORE", object())

    loader.disable("B")

    summary = loader.summary()

    assert summary["registered"] == 2
    assert summary["enabled"] == 1
    assert summary["disabled"] == 1

from OS import (
    AutonomousRuntime,
    RuntimeRegistry,
    RuntimeStatus,
)


def test_runtime_creation():
    runtime = AutonomousRuntime("MAIN")

    assert runtime.status == RuntimeStatus.CREATED


def test_runtime_start():
    runtime = AutonomousRuntime("MAIN")

    runtime.start()

    assert runtime.status == RuntimeStatus.RUNNING


def test_runtime_tick():
    runtime = AutonomousRuntime("MAIN")

    runtime.start()

    runtime.tick()
    runtime.tick()

    assert runtime.cycle == 2


def test_registry():
    registry = RuntimeRegistry()

    runtime = registry.create_runtime("MAIN")

    assert registry.get_runtime("MAIN") is runtime


def test_snapshot():
    registry = RuntimeRegistry()

    registry.create_runtime("MAIN")

    snapshot = registry.snapshot()

    assert "MAIN" in snapshot

from DIGITAL_EMPLOYEE.AUTONOMOUS import (
    AutonomousRuntime,
    AutonomousState,
)


def test_create_runtime():
    runtime = AutonomousRuntime()

    loop = runtime.create("EMP-001")

    assert loop.employee_id == "EMP-001"
    assert loop.state == AutonomousState.IDLE


def test_start_and_stop():
    runtime = AutonomousRuntime()

    loop = runtime.create("EMP-001")

    loop.start()

    assert loop.state == AutonomousState.RUNNING

    loop.stop()

    assert loop.state == AutonomousState.STOPPED


def test_single_step():
    runtime = AutonomousRuntime()

    loop = runtime.create("EMP-001")

    loop.start()

    result = loop.step(lambda: "DONE")

    assert result == "DONE"
    assert loop.iteration == 1
    assert loop.last_result == "DONE"


def test_history():
    runtime = AutonomousRuntime()

    loop = runtime.create("EMP-001")

    loop.start()

    loop.step(lambda: 1)
    loop.step(lambda: 2)

    assert len(loop.history) == 2


def test_snapshot():
    runtime = AutonomousRuntime()

    loop = runtime.create("EMP-001")

    snapshot = runtime.snapshot()

    assert loop.employee_id in snapshot

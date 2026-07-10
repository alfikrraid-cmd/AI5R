from datetime import UTC, datetime, timedelta

import pytest

from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus
from MANUFACTURING_CENTER.manufacturing_step import ManufacturingStep


def make_step(**overrides: object) -> ManufacturingStep:
    defaults: dict[str, object] = {
        "step_id": "step-1",
        "capability_id": "cap-1",
        "name": "Assemble Widget",
        "status": ManufacturingStatus.PENDING,
    }
    defaults.update(overrides)
    return ManufacturingStep(**defaults)  # type: ignore[arg-type]


def test_create_step() -> None:
    step = make_step()

    assert step.step_id == "step-1"
    assert step.capability_id == "cap-1"
    assert step.name == "Assemble Widget"
    assert step.status is ManufacturingStatus.PENDING
    assert step.started_at is None
    assert step.finished_at is None
    assert step.inputs == {}
    assert step.outputs == {}
    assert step.metadata == {}


def test_empty_step_id_raises() -> None:
    with pytest.raises(ValueError, match="step_id"):
        make_step(step_id="   ")


def test_empty_capability_id_raises() -> None:
    with pytest.raises(ValueError, match="capability_id"):
        make_step(capability_id="")


def test_empty_name_raises() -> None:
    with pytest.raises(ValueError, match="name"):
        make_step(name="")


def test_started_at_requires_timezone() -> None:
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        make_step(started_at=datetime.now())


def test_finished_at_requires_timezone() -> None:
    with pytest.raises(
        ValueError,
        match="finished_at must be timezone-aware",
    ):
        make_step(
            started_at=datetime.now(UTC),
            finished_at=datetime.now(),
        )


def test_finished_at_requires_started_at() -> None:
    with pytest.raises(
        ValueError,
        match="finished_at requires started_at",
    ):
        make_step(finished_at=datetime.now(UTC))


def test_finished_at_before_started_at_raises() -> None:
    started_at = datetime.now(UTC)
    finished_at = started_at - timedelta(seconds=5)

    with pytest.raises(
        ValueError,
        match="finished_at must not be earlier",
    ):
        make_step(
            started_at=started_at,
            finished_at=finished_at,
        )


def test_input_dictionaries_are_copied() -> None:
    inputs = {"source": "manual"}
    outputs = {"result": "pending"}
    metadata = {"owner": "Raka"}

    step = make_step(
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
    )

    inputs["source"] = "changed"
    outputs["result"] = "changed"
    metadata["owner"] = "changed"

    assert step.inputs == {"source": "manual"}
    assert step.outputs == {"result": "pending"}
    assert step.metadata == {"owner": "Raka"}


def test_start() -> None:
    step = make_step()

    step.start()

    assert step.status is ManufacturingStatus.MANUFACTURING
    assert step.started_at is not None
    assert step.started_at.tzinfo is not None


def test_start_twice_raises() -> None:
    step = make_step()
    step.start()

    with pytest.raises(
        RuntimeError,
        match="only start from pending",
    ):
        step.start()


def test_complete() -> None:
    step = make_step()
    step.start()

    step.complete(outputs={"result": "ok"})

    assert step.status is ManufacturingStatus.COMPLETED
    assert step.finished_at is not None
    assert step.outputs == {"result": "ok"}
    assert step.is_terminal is True


def test_complete_before_start_raises() -> None:
    step = make_step()

    with pytest.raises(
        RuntimeError,
        match="must be running",
    ):
        step.complete(outputs={})


def test_complete_twice_raises() -> None:
    step = make_step()
    step.start()
    step.complete(outputs={})

    with pytest.raises(
        RuntimeError,
        match="must be running",
    ):
        step.complete(outputs={})


def test_outputs_stored_independently() -> None:
    step = make_step()
    step.start()
    outputs = {"path": "/tmp/artifact"}

    step.complete(outputs=outputs)
    outputs["path"] = "mutated"

    assert step.outputs["path"] == "/tmp/artifact"


def test_fail() -> None:
    step = make_step()
    step.start()

    step.fail("capability unavailable")

    assert step.status is ManufacturingStatus.FAILED
    assert step.finished_at is not None
    assert step.metadata["reason"] == "capability unavailable"
    assert step.is_terminal is True


def test_fail_before_start_raises() -> None:
    step = make_step()

    with pytest.raises(
        RuntimeError,
        match="must be running",
    ):
        step.fail("error")


def test_fail_empty_reason_raises() -> None:
    step = make_step()
    step.start()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        step.fail("   ")


def test_cancel() -> None:
    step = make_step()
    step.start()

    step.cancel("no longer needed")

    assert step.status is ManufacturingStatus.CANCELLED
    assert step.finished_at is not None
    assert step.metadata["reason"] == "no longer needed"
    assert step.is_terminal is True


def test_cancel_before_start_raises() -> None:
    step = make_step()

    with pytest.raises(
        RuntimeError,
        match="must be running",
    ):
        step.cancel("cancelled")


def test_cancel_empty_reason_raises() -> None:
    step = make_step()
    step.start()

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        step.cancel("")


def test_terminal_step_cannot_fail_again() -> None:
    step = make_step()
    step.start()
    step.complete(outputs={})

    with pytest.raises(
        RuntimeError,
        match="must be running",
    ):
        step.fail("late failure")


def test_duration_none_before_start() -> None:
    step = make_step()

    assert step.duration is None


def test_duration_after_complete() -> None:
    step = make_step()
    step.start()
    step.complete(outputs={})

    assert step.duration is not None
    assert step.duration >= 0

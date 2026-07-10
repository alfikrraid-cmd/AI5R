from datetime import UTC, datetime, timedelta

import pytest

from MANUFACTURING_CENTER.manufacturing_result import ManufacturingResult
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus


def make_result() -> ManufacturingResult:
    return ManufacturingResult(
        manufacturing_id="MFG-001",
        status=ManufacturingStatus.MANUFACTURING,
        started_at=datetime.now(UTC) - timedelta(seconds=1),
    )


def test_create_manufacturing_result():
    result = make_result()

    assert result.manufacturing_id == "MFG-001"
    assert result.is_running is True
    assert result.is_completed is False
    assert result.is_failed is False


def test_requires_manufacturing_id():
    with pytest.raises(ValueError, match="manufacturing_id is required"):
        ManufacturingResult(
            manufacturing_id=" ",
            status=ManufacturingStatus.PENDING,
            started_at=datetime.now(UTC),
        )


def test_requires_timezone_aware_started_at():
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        ManufacturingResult(
            manufacturing_id="MFG-001",
            status=ManufacturingStatus.PENDING,
            started_at=datetime.now(),
        )


def test_rejects_negative_duration():
    with pytest.raises(
        ValueError,
        match="duration can never be negative",
    ):
        ManufacturingResult(
            manufacturing_id="MFG-001",
            status=ManufacturingStatus.PENDING,
            started_at=datetime.now(UTC),
            duration=-1,
        )


def test_complete():
    result = make_result()

    result.complete()

    assert result.status is ManufacturingStatus.COMPLETED
    assert result.finished_at is not None
    assert result.duration is not None
    assert result.duration >= 0
    assert result.is_completed is True
    assert result.is_running is False


def test_fail():
    result = make_result()

    result.fail("test failure")

    assert result.status is ManufacturingStatus.FAILED
    assert result.finished_at is not None
    assert result.duration is not None
    assert result.duration >= 0
    assert result.logs == ["Manufacturing failed: test failure"]


def test_fail_requires_reason():
    result = make_result()

    with pytest.raises(ValueError, match="failure reason is required"):
        result.fail(" ")


def test_terminal_result_cannot_be_completed_again():
    result = make_result()
    result.complete()

    with pytest.raises(
        RuntimeError,
        match="already terminal",
    ):
        result.complete()


def test_add_event_copies_event():
    result = make_result()
    event = {"type": "started"}

    result.add_event(event)
    event["type"] = "changed"

    assert result.events == [{"type": "started"}]


def test_add_log():
    result = make_result()

    result.add_log("  started  ")

    assert result.logs == ["started"]


def test_add_artifact():
    result = make_result()

    result.add_artifact("  build/app.zip  ")

    assert result.artifacts == ["build/app.zip"]

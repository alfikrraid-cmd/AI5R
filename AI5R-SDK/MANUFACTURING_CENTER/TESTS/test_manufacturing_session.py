from datetime import UTC, datetime
from pathlib import Path

import pytest

from MANUFACTURING.ORDERS import ManufacturingOrder

from MANUFACTURING_CENTER.manufacturing_context import ManufacturingContext
from MANUFACTURING_CENTER.manufacturing_session import ManufacturingSession
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus


def make_order() -> ManufacturingOrder:
    return ManufacturingOrder(
        order_id="MO-SESSION-001",
        product_name="LTSA",
        product_type="ENGINEERING_SYSTEM",
        requested_by="Chief",
    )


def make_context(tmp_path: Path) -> ManufacturingContext:
    return ManufacturingContext(
        manufacturing_id="SESSION-001",
        mwo={"order_id": "MO-SESSION-001"},
        product_name="LTSA",
        factory="AI5R Digital Factory",
        runtime="RuntimeEngine",
        workspace=tmp_path,
    )


def make_session(tmp_path: Path) -> ManufacturingSession:
    return ManufacturingSession(
        session_id="SESSION-001",
        order=make_order(),
        context=make_context(tmp_path),
    )


def test_create_pending_session(tmp_path: Path):
    session = make_session(tmp_path)

    assert session.status is ManufacturingStatus.PENDING
    assert session.progress == 0
    assert session.is_started is False
    assert session.is_terminal is False
    assert session.duration is None


def test_start_session(tmp_path: Path):
    session = make_session(tmp_path)

    session.start()

    assert session.status is ManufacturingStatus.VALIDATING
    assert session.started_at is not None
    assert session.started_at.tzinfo is not None
    assert len(session.status_history) == 1


def test_start_only_allowed_from_pending(tmp_path: Path):
    session = make_session(tmp_path)
    session.start()

    with pytest.raises(
        RuntimeError,
        match="only allowed from pending",
    ):
        session.start()


def test_transition_updates_stage_and_progress(tmp_path: Path):
    session = make_session(tmp_path)
    session.start()

    session.transition(
        ManufacturingStatus.PLANNING,
        stage=" Planning ",
        progress=20,
    )

    assert session.status is ManufacturingStatus.PLANNING
    assert session.current_stage == "Planning"
    assert session.progress == 20
    assert session.status_history[-1]["progress"] == 20


def test_transition_requires_started_session(tmp_path: Path):
    session = make_session(tmp_path)

    with pytest.raises(
        RuntimeError,
        match="must be started before transition",
    ):
        session.transition(ManufacturingStatus.PLANNING)


@pytest.mark.parametrize(
    "status",
    [
        ManufacturingStatus.COMPLETED,
        ManufacturingStatus.FAILED,
        ManufacturingStatus.CANCELLED,
    ],
)
def test_transition_rejects_terminal_target(
    tmp_path: Path,
    status: ManufacturingStatus,
):
    session = make_session(tmp_path)
    session.start()

    with pytest.raises(
        ValueError,
        match="use complete, fail, or cancel",
    ):
        session.transition(status)


def test_complete_returns_result(tmp_path: Path):
    session = make_session(tmp_path)
    session.start()
    session.transition(
        ManufacturingStatus.MANUFACTURING,
        stage="Execution",
        progress=75,
    )

    result = session.complete()

    assert session.status is ManufacturingStatus.COMPLETED
    assert session.progress == 100
    assert session.finished_at is not None
    assert result.status is ManufacturingStatus.COMPLETED
    assert result.duration is not None
    assert result.duration >= 0
    assert len(result.events) == 3


def test_fail_returns_result_with_reason(tmp_path: Path):
    session = make_session(tmp_path)
    session.start()

    result = session.fail(" capability failed ")

    assert session.status is ManufacturingStatus.FAILED
    assert result.status is ManufacturingStatus.FAILED
    assert result.logs == [
        "Manufacturing failed: capability failed"
    ]
    assert result.events[-1]["details"] == {
        "reason": "capability failed"
    }


def test_cancel_before_start_creates_zero_duration_result(
    tmp_path: Path,
):
    session = make_session(tmp_path)

    result = session.cancel("request withdrawn")

    assert session.status is ManufacturingStatus.CANCELLED
    assert session.started_at is not None
    assert session.finished_at is not None
    assert result.duration == 0
    assert result.logs == [
        "Manufacturing cancelled: request withdrawn"
    ]


def test_terminal_session_rejects_further_action(tmp_path: Path):
    session = make_session(tmp_path)
    session.complete()

    with pytest.raises(
        RuntimeError,
        match="terminal manufacturing session",
    ):
        session.fail("late failure")


def test_rejects_context_id_mismatch(tmp_path: Path):
    context = ManufacturingContext(
        manufacturing_id="DIFFERENT-ID",
        mwo={"order_id": "MO-SESSION-001"},
        product_name="LTSA",
        factory="AI5R Digital Factory",
        runtime="RuntimeEngine",
        workspace=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="context.manufacturing_id must equal session_id",
    ):
        ManufacturingSession(
            session_id="SESSION-001",
            order=make_order(),
            context=context,
        )


def test_rejects_naive_started_at(tmp_path: Path):
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        ManufacturingSession(
            session_id="SESSION-001",
            order=make_order(),
            context=make_context(tmp_path),
            started_at=datetime.now(),
        )


def test_metadata_is_defensively_copied(tmp_path: Path):
    metadata = {"owner": "Maya"}

    session = ManufacturingSession(
        session_id="SESSION-001",
        order=make_order(),
        context=make_context(tmp_path),
        metadata=metadata,
    )

    metadata["owner"] = "changed"

    assert session.metadata == {"owner": "Maya"}

from pathlib import Path

import pytest

from MANUFACTURING.ORDERS import ManufacturingOrder
from RUNTIME import RuntimeResponse, RuntimeStatus

from MANUFACTURING_CENTER.manufacturing_context import ManufacturingContext
from MANUFACTURING_CENTER.manufacturing_execution_adapter import (
    ManufacturingExecutionAdapter,
)
from MANUFACTURING_CENTER.manufacturing_session import ManufacturingSession
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus
from MANUFACTURING_CENTER.manufacturing_step import ManufacturingStep


def make_session(tmp_path: Path) -> ManufacturingSession:
    order = ManufacturingOrder(
        order_id="MO-ADAPTER-001",
        product_name="LTSA",
        product_type="ENGINEERING_SYSTEM",
        requested_by="Chief",
    )

    context = ManufacturingContext(
        manufacturing_id="SESSION-ADAPTER-001",
        mwo={"order_id": order.order_id},
        product_name="LTSA",
        factory="AI5R Digital Factory",
        runtime="RuntimeEngine",
        workspace=tmp_path,
    )

    session = ManufacturingSession(
        session_id="SESSION-ADAPTER-001",
        order=order,
        context=context,
        metadata={"owner": "Maya"},
    )
    session.start()
    session.transition(
        ManufacturingStatus.MANUFACTURING,
        stage="Execution",
        progress=50,
    )
    return session


def make_step() -> ManufacturingStep:
    step = ManufacturingStep(
        step_id="STEP-001",
        capability_id="BUILD_PRODUCT",
        name="Build Product",
        metadata={"owner": "Raka"},
    )
    step.start()
    return step


def test_adapt_success(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    step = make_step()

    response = RuntimeResponse(
        status=RuntimeStatus.SUCCESS,
        profile="manufacturing",
        definition="BUILD_PRODUCT",
        output={
            "product": "LTSA",
            "artifacts": [
                " build/app.zip ",
                "",
                "build/report.pdf",
            ],
        },
        metadata={"factory_id": "DF-001"},
    )

    result = ManufacturingExecutionAdapter().adapt(
        response=response,
        session=session,
        step=step,
    )

    assert step.status is ManufacturingStatus.COMPLETED
    assert session.status is ManufacturingStatus.COMPLETED
    assert session.progress == 100
    assert result.status is ManufacturingStatus.COMPLETED
    assert result.artifacts == [
        "build/app.zip",
        "build/report.pdf",
    ]
    assert result.metadata["factory_id"] == "DF-001"
    assert result.metadata["owner"] == "Maya"
    assert result.metadata["runtime_definition"] == "BUILD_PRODUCT"
    assert result.metadata["runtime_output"]["product"] == "LTSA"


def test_adapt_failure(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    step = make_step()

    response = RuntimeResponse(
        status=RuntimeStatus.FAILED,
        profile="manufacturing",
        definition="BUILD_PRODUCT",
        metadata={"factory_id": "DF-001"},
        error=" capability failed ",
    )

    result = ManufacturingExecutionAdapter().adapt(
        response=response,
        session=session,
        step=step,
    )

    assert step.status is ManufacturingStatus.FAILED
    assert step.metadata["reason"] == "capability failed"
    assert session.status is ManufacturingStatus.FAILED
    assert result.status is ManufacturingStatus.FAILED
    assert result.logs == [
        "Manufacturing failed: capability failed"
    ]
    assert result.metadata["runtime_definition"] == "BUILD_PRODUCT"


def test_requires_started_session(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    session.started_at = None
    step = make_step()

    response = RuntimeResponse(
        status=RuntimeStatus.SUCCESS,
        profile="manufacturing",
        definition="BUILD_PRODUCT",
    )

    with pytest.raises(ValueError, match="session must be started"):
        ManufacturingExecutionAdapter().adapt(
            response=response,
            session=session,
            step=step,
        )


def test_requires_running_step(tmp_path: Path) -> None:
    session = make_session(tmp_path)

    step = ManufacturingStep(
        step_id="STEP-001",
        capability_id="BUILD_PRODUCT",
        name="Build Product",
    )

    response = RuntimeResponse(
        status=RuntimeStatus.SUCCESS,
        profile="manufacturing",
        definition="BUILD_PRODUCT",
    )

    with pytest.raises(
        ValueError,
        match="step must be in MANUFACTURING status",
    ):
        ManufacturingExecutionAdapter().adapt(
            response=response,
            session=session,
            step=step,
        )


def test_failed_response_requires_error(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    step = make_step()

    response = RuntimeResponse(
        status=RuntimeStatus.FAILED,
        profile="manufacturing",
        definition="BUILD_PRODUCT",
        error=None,
    )

    with pytest.raises(
        ValueError,
        match="response.error must not be empty",
    ):
        ManufacturingExecutionAdapter().adapt(
            response=response,
            session=session,
            step=step,
        )


@pytest.mark.parametrize(
    "artifacts",
    [
        123,
        {"path": "build/app.zip"},
        ["build/app.zip", 123],
    ],
)
def test_rejects_invalid_artifacts(
    tmp_path: Path,
    artifacts: object,
) -> None:
    session = make_session(tmp_path)
    step = make_step()

    response = RuntimeResponse(
        status=RuntimeStatus.SUCCESS,
        profile="manufacturing",
        definition="BUILD_PRODUCT",
        output={"artifacts": artifacts},
    )

    with pytest.raises(TypeError):
        ManufacturingExecutionAdapter().adapt(
            response=response,
            session=session,
            step=step,
        )


def test_does_not_mutate_runtime_response(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    step = make_step()

    output = {
        "artifacts": [" build/app.zip "],
        "value": 1,
    }
    metadata = {"factory_id": "DF-001"}

    response = RuntimeResponse(
        status=RuntimeStatus.SUCCESS,
        profile="manufacturing",
        definition="BUILD_PRODUCT",
        output=output,
        metadata=metadata,
    )

    ManufacturingExecutionAdapter().adapt(
        response=response,
        session=session,
        step=step,
    )

    assert response.output == {
        "artifacts": [" build/app.zip "],
        "value": 1,
    }
    assert response.metadata == {"factory_id": "DF-001"}


def test_preserves_existing_result_metadata(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    session.metadata["factory_id"] = "ORIGINAL"
    step = make_step()

    response = RuntimeResponse(
        status=RuntimeStatus.SUCCESS,
        profile="manufacturing",
        definition="BUILD_PRODUCT",
        metadata={"factory_id": "NEW"},
    )

    result = ManufacturingExecutionAdapter().adapt(
        response=response,
        session=session,
        step=step,
    )

    assert result.metadata["factory_id"] == "ORIGINAL"

from RUNTIME import (
    RuntimeEngine,
    RuntimeStatus,
)


def test_runtime_executes_pipeline_in_order():
    engine = RuntimeEngine()

    def step_one(request):
        return {
            **request.payload,
            "requirements": "captured",
        }

    def step_two(request):
        return {
            **request.payload,
            "architecture": "created",
        }

    engine.register_handler("manufacturing", "requirements", step_one)
    engine.register_handler("manufacturing", "architecture", step_two)

    response = engine.execute_pipeline(
        profile="manufacturing",
        definitions=("requirements", "architecture"),
        payload={
            "product": "Website",
        },
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["product"] == "Website"
    assert response.output["requirements"] == "captured"
    assert response.output["architecture"] == "created"
    assert response.definition == "architecture"


def test_runtime_pipeline_falls_back_for_missing_handler():
    engine = RuntimeEngine()

    def step_two(request):
        return {
            **request.payload,
            "completed": True,
        }

    engine.register_handler("manufacturing", "final_step", step_two)

    response = engine.execute_pipeline(
        profile="manufacturing",
        definitions=("missing_step", "final_step"),
        payload={
            "product": "AI Agent",
        },
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["product"] == "AI Agent"
    assert response.output["completed"] is True


def test_runtime_pipeline_stops_on_failure():
    engine = RuntimeEngine()

    def step_one(request):
        return {
            "started": True,
        }

    def broken_step(request):
        raise ValueError("pipeline failed")

    def step_three(request):
        return {
            "should_not_run": True,
        }

    engine.register_handler("manufacturing", "start", step_one)
    engine.register_handler("manufacturing", "broken", broken_step)
    engine.register_handler("manufacturing", "end", step_three)

    response = engine.execute_pipeline(
        profile="manufacturing",
        definitions=("start", "broken", "end"),
    )

    assert response.status == RuntimeStatus.FAILED
    assert response.error == "pipeline failed"
    assert response.definition == "broken"


def test_runtime_pipeline_requires_definitions():
    engine = RuntimeEngine()

    try:
        engine.execute_pipeline(
            profile="manufacturing",
            definitions=(),
        )
    except ValueError as exc:
        assert str(exc) == "definitions are required"
    else:
        raise AssertionError("Expected ValueError")

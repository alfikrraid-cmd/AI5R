from RUNTIME import (
    RuntimeEngine,
    RuntimeStatus,
)


def test_runtime_registers_capability():
    engine = RuntimeEngine()

    def requirement_analysis(request):
        return {
            "requirements_analyzed": True,
        }

    engine.register_capability(
        profile="manufacturing",
        capability_id="REQUIREMENT_ANALYSIS",
        handler=requirement_analysis,
    )

    assert engine.has_capability("manufacturing", "REQUIREMENT_ANALYSIS") is True


def test_runtime_executes_registered_capability():
    engine = RuntimeEngine()

    def requirement_analysis(request):
        return {
            **request.payload,
            "requirements_analyzed": True,
        }

    engine.register_capability(
        profile="manufacturing",
        capability_id="REQUIREMENT_ANALYSIS",
        handler=requirement_analysis,
    )

    response = engine.execute_capability_pipeline(
        profile="manufacturing",
        capability_ids=("REQUIREMENT_ANALYSIS",),
        payload={
            "product": "Website",
        },
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["product"] == "Website"
    assert response.output["requirements_analyzed"] is True


def test_runtime_executes_multiple_capabilities_in_order():
    engine = RuntimeEngine()

    def requirement_analysis(request):
        return {
            **request.payload,
            "requirements_analyzed": True,
        }

    def architecture_design(request):
        return {
            **request.payload,
            "architecture_designed": True,
        }

    engine.register_capability(
        profile="manufacturing",
        capability_id="REQUIREMENT_ANALYSIS",
        handler=requirement_analysis,
    )
    engine.register_capability(
        profile="manufacturing",
        capability_id="ARCHITECTURE_DESIGN",
        handler=architecture_design,
    )

    response = engine.execute_capability_pipeline(
        profile="manufacturing",
        capability_ids=(
            "REQUIREMENT_ANALYSIS",
            "ARCHITECTURE_DESIGN",
        ),
        payload={
            "product": "AI Agent",
        },
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.definition == "ARCHITECTURE_DESIGN"
    assert response.output["requirements_analyzed"] is True
    assert response.output["architecture_designed"] is True


def test_runtime_capability_pipeline_stops_on_failure():
    engine = RuntimeEngine()

    def requirement_analysis(request):
        return {
            "requirements_analyzed": True,
        }

    def broken_capability(request):
        raise ValueError("capability failed")

    engine.register_capability(
        profile="manufacturing",
        capability_id="REQUIREMENT_ANALYSIS",
        handler=requirement_analysis,
    )
    engine.register_capability(
        profile="manufacturing",
        capability_id="BROKEN_CAPABILITY",
        handler=broken_capability,
    )

    response = engine.execute_capability_pipeline(
        profile="manufacturing",
        capability_ids=(
            "REQUIREMENT_ANALYSIS",
            "BROKEN_CAPABILITY",
        ),
    )

    assert response.status == RuntimeStatus.FAILED
    assert response.definition == "BROKEN_CAPABILITY"
    assert response.error == "capability failed"

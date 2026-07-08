from RUNTIME import (
    RuntimeEngine,
    RuntimeRequest,
    RuntimeStatus,
)


def test_runtime_registers_handler():
    engine = RuntimeEngine()

    def website_handler(request):
        return {
            "manufactured": request.payload["product"],
        }

    engine.register_handler(
        profile="manufacturing",
        definition="website_recipe",
        handler=website_handler,
    )

    assert engine.has_handler("manufacturing", "website_recipe") is True


def test_runtime_executes_registered_handler():
    engine = RuntimeEngine()

    def website_handler(request):
        return {
            "manufactured": request.payload["product"],
            "profile": request.profile,
        }

    engine.register_handler(
        profile="manufacturing",
        definition="website_recipe",
        handler=website_handler,
    )

    response = engine.execute(
        RuntimeRequest(
            profile="manufacturing",
            definition="website_recipe",
            payload={
                "product": "Website",
            },
        )
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["manufactured"] == "Website"
    assert response.output["profile"] == "manufacturing"


def test_runtime_falls_back_to_echo_when_handler_missing():
    engine = RuntimeEngine()

    response = engine.execute(
        RuntimeRequest(
            profile="manufacturing",
            definition="unknown_recipe",
            payload={
                "product": "Unknown",
            },
        )
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["product"] == "Unknown"


def test_runtime_returns_failed_response_when_handler_raises():
    engine = RuntimeEngine()

    def broken_handler(request):
        raise ValueError("station failed")

    engine.register_handler(
        profile="manufacturing",
        definition="broken_recipe",
        handler=broken_handler,
    )

    response = engine.execute(
        RuntimeRequest(
            profile="manufacturing",
            definition="broken_recipe",
        )
    )

    assert response.status == RuntimeStatus.FAILED
    assert response.error == "station failed"


def test_runtime_rejects_empty_profile_registration():
    engine = RuntimeEngine()

    def handler(request):
        return {}

    try:
        engine.register_handler("", "definition", handler)
    except ValueError as exc:
        assert str(exc) == "profile is required"
    else:
        raise AssertionError("Expected ValueError")


def test_runtime_rejects_empty_definition_registration():
    engine = RuntimeEngine()

    def handler(request):
        return {}

    try:
        engine.register_handler("profile", "", handler)
    except ValueError as exc:
        assert str(exc) == "definition is required"
    else:
        raise AssertionError("Expected ValueError")

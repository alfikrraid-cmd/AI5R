from RUNTIME import (
    RuntimeEngine,
    RuntimeRequest,
    RuntimeStatus,
)


def test_runtime_executes_request():

    engine = RuntimeEngine()

    request = RuntimeRequest(
        profile="manufacturing",
        definition="website_recipe",
        payload={
            "product": "Website",
        },
    )

    response = engine.execute(request)

    assert response.status == RuntimeStatus.SUCCESS
    assert response.profile == "manufacturing"
    assert response.definition == "website_recipe"
    assert response.output["product"] == "Website"


def test_runtime_preserves_metadata():

    engine = RuntimeEngine()

    request = RuntimeRequest(
        profile="finance",
        definition="journal_entry",
        metadata={
            "company": "PT Mitra Andalan Servisindo",
        },
    )

    response = engine.execute(request)

    assert response.metadata["company"] == "PT Mitra Andalan Servisindo"


def test_runtime_engine_name():

    engine = RuntimeEngine()

    assert engine.engine_name == "AI5R Canonical Runtime Engine"

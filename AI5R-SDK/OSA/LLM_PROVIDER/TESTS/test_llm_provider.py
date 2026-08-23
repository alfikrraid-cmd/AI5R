import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.LLM_PROVIDER import (
    LLMProviderRegistry,
    LLMRequest,
    MockLLMProvider,
)


def test_register_provider():
    registry = LLMProviderRegistry()
    provider = MockLLMProvider()

    registry.register(provider)

    assert registry.resolve("MOCK") is provider


def test_mock_provider_generates_response():
    provider = MockLLMProvider()

    response = provider.generate(
        LLMRequest(
            prompt="hello AI5R",
        )
    )

    assert response.provider == "MOCK"
    assert response.model == "mock-model"
    assert response.content == "MOCK_RESPONSE::hello AI5R"
    assert response.finish_reason == "stop"


def test_unknown_provider():
    registry = LLMProviderRegistry()

    try:
        registry.resolve("OPENAI")
    except ValueError as e:
        assert str(e) == "provider is not registered"
    else:
        raise AssertionError()


def test_prompt_required():
    provider = MockLLMProvider()

    try:
        provider.generate(LLMRequest(prompt=""))
    except ValueError as e:
        assert str(e) == "prompt is required"
    else:
        raise AssertionError()


def test_default_health_is_healthy():
    provider = MockLLMProvider()

    status = provider.health()

    assert status.provider == "MOCK"
    assert status.healthy is True


def test_default_estimate_cost_is_zero():
    provider = MockLLMProvider()

    estimate = provider.estimate_cost(LLMRequest(prompt="hello"))

    assert estimate.provider == "MOCK"
    assert estimate.estimated_usd == 0.0


def test_default_supported_capabilities_is_chat():
    provider = MockLLMProvider()

    assert provider.supported_capabilities() == frozenset({"chat"})


def test_default_stream_not_implemented():
    provider = MockLLMProvider()

    try:
        provider.stream(LLMRequest(prompt="hello"))
    except NotImplementedError:
        pass
    else:
        raise AssertionError()


def test_default_embeddings_not_implemented():
    from OSA.LLM_PROVIDER import EmbeddingsRequest

    provider = MockLLMProvider()

    try:
        provider.embeddings(EmbeddingsRequest(input=["hello"]))
    except NotImplementedError:
        pass
    else:
        raise AssertionError()

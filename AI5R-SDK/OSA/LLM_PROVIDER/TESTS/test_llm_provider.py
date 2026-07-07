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

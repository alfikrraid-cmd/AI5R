import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.LLM_PROVIDER import LLMProviderRegistry, LLMRequest
from OSA.LLM_PROVIDER_OPENAI import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(
            {
                "model": "test-model",
                "choices": [
                    {
                        "message": {
                            "content": "real provider response",
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
        ).encode("utf-8")


def test_openai_compatible_provider_registers():
    registry = LLMProviderRegistry()
    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(api_key="test-key")
    )

    registry.register(provider)

    assert registry.resolve("OPENAI_COMPATIBLE") is provider


def test_openai_compatible_provider_generates_response():
    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(
            api_key="test-key",
            model="test-model",
            base_url="https://example.test/v1/chat/completions",
        )
    )

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(
            LLMRequest(
                prompt="hello",
                system_prompt="You are AI5R.",
                temperature=0.1,
            )
        )

    assert response.provider == "OPENAI_COMPATIBLE"
    assert response.model == "test-model"
    assert response.content == "real provider response"
    assert response.finish_reason == "stop"


def test_openai_compatible_provider_requires_prompt():
    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(api_key="test-key")
    )

    try:
        provider.generate(LLMRequest(prompt=""))
    except ValueError as error:
        assert str(error) == "prompt is required"
    else:
        raise AssertionError("ValueError was not raised")


def test_openai_compatible_provider_requires_api_key():
    provider = OpenAICompatibleProvider(
        OpenAICompatibleConfig(api_key="")
    )

    try:
        provider.generate(LLMRequest(prompt="hello"))
    except ValueError as error:
        assert str(error) == "api_key is required"
    else:
        raise AssertionError("ValueError was not raised")

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.providers.openrouter_provider import OpenRouterProvider
from OSA.LLM_PROVIDER import LLMRequest
from OSA.LLM_PROVIDER_OPENAI import OpenAICompatibleConfig, OpenAICompatibleProvider


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(
            {
                "model": "openrouter/auto",
                "choices": [{"message": {"content": "hi from openrouter"}, "finish_reason": "stop"}],
            }
        ).encode("utf-8")


def test_openrouter_provider_is_an_openai_compatible_provider():
    assert issubclass(OpenRouterProvider, OpenAICompatibleProvider)


def test_openrouter_provider_name():
    provider = OpenRouterProvider(OpenAICompatibleConfig(api_key="key"))
    assert provider.provider_name == "OPENROUTER"


def test_openrouter_default_base_url():
    provider = OpenRouterProvider()
    assert "openrouter.ai" in provider.config.base_url


def test_openrouter_provider_generates_via_inherited_logic():
    provider = OpenRouterProvider(OpenAICompatibleConfig(api_key="key", model="openrouter/auto"))

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(LLMRequest(prompt="hello"))

    assert response.provider == "OPENROUTER"
    assert response.content == "hi from openrouter"


def test_openrouter_provider_supported_capabilities():
    provider = OpenRouterProvider(OpenAICompatibleConfig(api_key="key"))
    assert "translation" in provider.supported_capabilities()

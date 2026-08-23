import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.providers.litellm_provider import LiteLLMProvider
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
                "model": "gpt-4o-mini",
                "choices": [{"message": {"content": "hi from litellm"}, "finish_reason": "stop"}],
            }
        ).encode("utf-8")


def test_litellm_provider_is_an_openai_compatible_provider():
    assert issubclass(LiteLLMProvider, OpenAICompatibleProvider)


def test_litellm_provider_name():
    provider = LiteLLMProvider(OpenAICompatibleConfig(api_key="key"))
    assert provider.provider_name == "LITELLM"


def test_litellm_default_base_url_is_local_proxy():
    provider = LiteLLMProvider()
    assert "localhost" in provider.config.base_url


def test_litellm_provider_generates_via_inherited_logic():
    provider = LiteLLMProvider(OpenAICompatibleConfig(api_key="key", model="gpt-4o-mini"))

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(LLMRequest(prompt="hello"))

    assert response.provider == "LITELLM"
    assert response.content == "hi from litellm"


def test_litellm_provider_supported_capabilities():
    provider = LiteLLMProvider(OpenAICompatibleConfig(api_key="key"))
    assert "tool_calling" in provider.supported_capabilities()

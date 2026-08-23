import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.providers.deepseek_provider import DeepSeekProvider
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
                "model": "deepseek-chat",
                "choices": [{"message": {"content": "hi from deepseek"}, "finish_reason": "stop"}],
            }
        ).encode("utf-8")


def test_deepseek_provider_is_an_openai_compatible_provider():
    assert issubclass(DeepSeekProvider, OpenAICompatibleProvider)


def test_deepseek_provider_name():
    provider = DeepSeekProvider(OpenAICompatibleConfig(api_key="key"))
    assert provider.provider_name == "DEEPSEEK"


def test_deepseek_default_base_url():
    provider = DeepSeekProvider()
    assert "deepseek.com" in provider.config.base_url


def test_deepseek_provider_generates_via_inherited_logic():
    provider = DeepSeekProvider(OpenAICompatibleConfig(api_key="key", model="deepseek-chat"))

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(LLMRequest(prompt="hello"))

    assert response.provider == "DEEPSEEK"
    assert response.content == "hi from deepseek"


def test_deepseek_provider_supported_capabilities():
    provider = DeepSeekProvider(OpenAICompatibleConfig(api_key="key"))
    assert provider.supported_capabilities() == frozenset({"chat", "coding", "reasoning"})

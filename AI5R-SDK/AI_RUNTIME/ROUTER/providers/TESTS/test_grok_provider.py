import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.providers.grok_provider import GrokProvider
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
                "model": "grok-beta",
                "choices": [{"message": {"content": "hi from grok"}, "finish_reason": "stop"}],
            }
        ).encode("utf-8")


def test_grok_provider_is_an_openai_compatible_provider():
    assert issubclass(GrokProvider, OpenAICompatibleProvider)


def test_grok_provider_name():
    provider = GrokProvider(OpenAICompatibleConfig(api_key="key"))
    assert provider.provider_name == "GROK"


def test_grok_default_base_url():
    provider = GrokProvider()
    assert "x.ai" in provider.config.base_url


def test_grok_provider_generates_via_inherited_logic():
    provider = GrokProvider(OpenAICompatibleConfig(api_key="key", model="grok-beta"))

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(LLMRequest(prompt="hello"))

    assert response.provider == "GROK"
    assert response.content == "hi from grok"


def test_grok_provider_supported_capabilities():
    provider = GrokProvider(OpenAICompatibleConfig(api_key="key"))
    assert provider.supported_capabilities() == frozenset({"chat", "reasoning", "coding"})

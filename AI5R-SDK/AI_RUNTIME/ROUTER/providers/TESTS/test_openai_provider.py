import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.providers.openai_provider import OpenAIProvider
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
                "choices": [{"message": {"content": "hi from openai"}, "finish_reason": "stop"}],
            }
        ).encode("utf-8")


def test_openai_provider_is_an_openai_compatible_provider():
    assert issubclass(OpenAIProvider, OpenAICompatibleProvider)


def test_openai_provider_name():
    provider = OpenAIProvider(OpenAICompatibleConfig(api_key="key"))
    assert provider.provider_name == "OPENAI"


def test_openai_provider_generates_via_inherited_logic():
    provider = OpenAIProvider(OpenAICompatibleConfig(api_key="key", model="gpt-4o-mini"))

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(LLMRequest(prompt="hello"))

    assert response.provider == "OPENAI"
    assert response.content == "hi from openai"


def test_openai_provider_supported_capabilities_includes_coding():
    provider = OpenAIProvider(OpenAICompatibleConfig(api_key="key"))
    assert "coding" in provider.supported_capabilities()
    assert "chat" in provider.supported_capabilities()

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.providers.gemini_provider import GeminiConfig, GeminiProvider
from OSA.LLM_PROVIDER import LLMRequest


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "hi from gemini"}]},
                        "finishReason": "STOP",
                    }
                ]
            }
        ).encode("utf-8")


def test_gemini_provider_name():
    provider = GeminiProvider(GeminiConfig(api_key="key"))
    assert provider.provider_name == "GEMINI"


def test_gemini_provider_generates_response():
    provider = GeminiProvider(GeminiConfig(api_key="key", model="gemini-1.5-flash"))

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(LLMRequest(prompt="hello"))

    assert response.provider == "GEMINI"
    assert response.content == "hi from gemini"
    assert response.finish_reason == "STOP"


def test_gemini_provider_requires_prompt():
    provider = GeminiProvider(GeminiConfig(api_key="key"))

    with pytest.raises(ValueError):
        provider.generate(LLMRequest(prompt=""))


def test_gemini_provider_requires_api_key():
    provider = GeminiProvider(GeminiConfig(api_key=""))

    with pytest.raises(ValueError):
        provider.generate(LLMRequest(prompt="hello"))


def test_gemini_provider_supported_capabilities():
    provider = GeminiProvider(GeminiConfig(api_key="key"))
    capabilities = provider.supported_capabilities()
    assert "vision" in capabilities
    assert "ocr" in capabilities

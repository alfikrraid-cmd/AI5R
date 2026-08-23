import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.providers.ollama_provider import OllamaConfig, OllamaProvider
from OSA.LLM_PROVIDER import LLMRequest


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(
            {"model": "llama3", "response": "hi from ollama", "done": True}
        ).encode("utf-8")


def test_ollama_provider_name():
    provider = OllamaProvider()
    assert provider.provider_name == "OLLAMA"


def test_ollama_provider_generates_response():
    provider = OllamaProvider(OllamaConfig(model="llama3", base_url="http://localhost:11434"))

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(LLMRequest(prompt="hello"))

    assert response.provider == "OLLAMA"
    assert response.content == "hi from ollama"
    assert response.finish_reason == "stop"


def test_ollama_provider_requires_prompt():
    provider = OllamaProvider()

    with pytest.raises(ValueError):
        provider.generate(LLMRequest(prompt=""))


def test_ollama_provider_health_is_healthy_local():
    provider = OllamaProvider()
    status = provider.health()
    assert status.healthy is True


def test_ollama_provider_supported_capabilities():
    provider = OllamaProvider()
    assert provider.supported_capabilities() == frozenset({"chat", "coding", "reasoning"})

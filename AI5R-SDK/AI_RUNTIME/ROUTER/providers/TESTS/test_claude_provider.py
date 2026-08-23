import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.providers.claude_provider import ClaudeConfig, ClaudeProvider
from OSA.LLM_PROVIDER import LLMRequest


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(
            {
                "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": "hi from claude"}],
                "stop_reason": "end_turn",
            }
        ).encode("utf-8")


def test_claude_provider_name():
    provider = ClaudeProvider(ClaudeConfig(api_key="key"))
    assert provider.provider_name == "CLAUDE"


def test_claude_provider_generates_response():
    provider = ClaudeProvider(ClaudeConfig(api_key="key", model="claude-sonnet-5"))

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = provider.generate(LLMRequest(prompt="hello", system_prompt="You are AI5R."))

    assert response.provider == "CLAUDE"
    assert response.content == "hi from claude"
    assert response.finish_reason == "end_turn"


def test_claude_provider_requires_prompt():
    provider = ClaudeProvider(ClaudeConfig(api_key="key"))

    with pytest.raises(ValueError):
        provider.generate(LLMRequest(prompt=""))


def test_claude_provider_requires_api_key():
    provider = ClaudeProvider(ClaudeConfig(api_key=""))

    with pytest.raises(ValueError):
        provider.generate(LLMRequest(prompt="hello"))


def test_claude_provider_supported_capabilities():
    provider = ClaudeProvider(ClaudeConfig(api_key="key"))
    capabilities = provider.supported_capabilities()
    assert "architecture" in capabilities
    assert "vision" in capabilities

import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
_SDK = ROOT / "AI5R-SDK"
if str(_SDK) not in sys.path:
    sys.path.insert(0, str(_SDK))

from AI_RUNTIME.ROUTER.providers import DahonoProvider as ExportedDahonoProvider
from AI_RUNTIME.ROUTER.providers.dahono_provider import DahonoProvider
from AI_RUNTIME.ROUTER.providers import ClaudeProvider, OllamaProvider
from AI_RUNTIME.ROUTER.router import Router
from OSA.LLM_PROVIDER import BaseLLMProvider, LLMRequest
from OSA.LLM_PROVIDER_OPENAI import OpenAICompatibleConfig, OpenAICompatibleProvider

ENV_KEYS = (
    "AI5R_DAHONO_API_KEY",
    "AI5R_DAHONO_BASE_URL",
    "AI5R_DAHONO_MODEL",
    "AI5R_CLAUDE_API_KEY",
    "AI5R_OPENAI_API_KEY",
    "AI5R_OPENROUTER_API_KEY",
    "AI5R_GEMINI_API_KEY",
    "AI5R_DEEPSEEK_API_KEY",
    "AI5R_GROK_API_KEY",
    "AI5R_LITELLM_API_KEY",
)

FAKE_KEY = "test-key-not-real"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(
            {
                "model": "echo-model",
                "choices": [{"message": {"content": "hi from dahono"}, "finish_reason": "stop"}],
            }
        ).encode("utf-8")


def _configured(monkeypatch):
    monkeypatch.setenv("AI5R_DAHONO_API_KEY", FAKE_KEY)
    monkeypatch.setenv("AI5R_DAHONO_MODEL", "some-model")


def test_provider_name_and_inheritance():
    assert DahonoProvider.provider_name == "DAHONO"
    assert issubclass(DahonoProvider, OpenAICompatibleProvider)
    assert ExportedDahonoProvider is DahonoProvider


def test_default_base_url_is_chat_completions():
    assert DahonoProvider().config.base_url == "https://gateway.dahono.com/v1/chat/completions"


def test_base_url_from_env_appends_chat_path(monkeypatch):
    monkeypatch.setenv("AI5R_DAHONO_BASE_URL", "https://example.test/v1/")
    assert DahonoProvider().config.base_url == "https://example.test/v1/chat/completions"
    monkeypatch.setenv("AI5R_DAHONO_BASE_URL", "https://example.test/v1/chat/completions")
    assert DahonoProvider().config.base_url == "https://example.test/v1/chat/completions"


def test_api_key_and_model_read_from_env_no_default_model(monkeypatch):
    assert DahonoProvider().config.model == ""
    _configured(monkeypatch)
    provider = DahonoProvider()
    assert provider.config.api_key == FAKE_KEY
    assert provider.config.model == "some-model"


def test_missing_key_fails_safe(monkeypatch):
    monkeypatch.setenv("AI5R_DAHONO_MODEL", "some-model")
    provider = DahonoProvider()
    assert provider.health().healthy is False
    assert DahonoProvider.from_env() is None
    with patch("urllib.request.urlopen") as urlopen:
        with pytest.raises(ValueError):
            provider.generate(LLMRequest(prompt="hello"))
    urlopen.assert_not_called()


def test_missing_model_fails_safe(monkeypatch):
    monkeypatch.setenv("AI5R_DAHONO_API_KEY", FAKE_KEY)
    provider = DahonoProvider()
    assert provider.health().healthy is False
    assert DahonoProvider.from_env() is None
    with patch("urllib.request.urlopen") as urlopen:
        with pytest.raises(ValueError, match="model"):
            provider.generate(LLMRequest(prompt="hello"))
    urlopen.assert_not_called()


def test_bearer_auth_and_chat_request_mapping(monkeypatch):
    _configured(monkeypatch)
    provider = DahonoProvider()
    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()) as urlopen:
        provider.generate(LLMRequest(prompt="hello", system_prompt="be brief", temperature=0.5))

    http_request = urlopen.call_args.args[0]
    assert http_request.full_url == "https://gateway.dahono.com/v1/chat/completions"
    assert http_request.get_method() == "POST"
    assert http_request.get_header("Authorization") == f"Bearer {FAKE_KEY}"
    body = json.loads(http_request.data.decode("utf-8"))
    assert body == {
        "model": "some-model",
        "temperature": 0.5,
        "messages": [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "hello"},
        ],
    }


def test_response_mapping_to_llm_response(monkeypatch):
    _configured(monkeypatch)
    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
        response = DahonoProvider().generate(LLMRequest(prompt="hello"))
    assert response.provider == "DAHONO"
    assert response.model == "echo-model"
    assert response.content == "hi from dahono"
    assert response.finish_reason == "stop"


def test_supported_capabilities_exact_and_no_vision_ocr_tools_embedding():
    caps = DahonoProvider(OpenAICompatibleConfig(api_key="k", model="m")).supported_capabilities()
    assert caps == frozenset({"chat", "coding", "reasoning", "summarization", "translation"})
    for banned in ("vision", "ocr", "tool_calling", "embedding"):
        assert banned not in caps


def test_no_stream_or_embeddings_implementation_added():
    assert DahonoProvider.stream is BaseLLMProvider.stream
    assert DahonoProvider.embeddings is BaseLLMProvider.embeddings
    assert "stream" not in DahonoProvider.__dict__


def test_no_key_or_body_logged(monkeypatch, caplog):
    _configured(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        with patch("urllib.request.urlopen", return_value=FakeHTTPResponse()):
            DahonoProvider().generate(LLMRequest(prompt="proprietary-secret-prompt"))
    assert FAKE_KEY not in caplog.text
    assert "proprietary-secret-prompt" not in caplog.text


def _provider_names(client):
    return [p.provider_name for p in client._router.provider_registry.list_all()]


@pytest.fixture
def dependencies_module():
    backend_api = ROOT / "CORE-SERVICES" / "BACKEND-API"
    core_services = ROOT / "CORE-SERVICES"
    for path in (backend_api, core_services):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import dependencies

    return dependencies


def test_registration_with_key_and_model(monkeypatch, dependencies_module):
    _configured(monkeypatch)
    names = _provider_names(dependencies_module._build_copilot_ai_client())
    assert "DAHONO" in names


def test_no_registration_without_key(monkeypatch, dependencies_module):
    monkeypatch.setenv("AI5R_DAHONO_MODEL", "some-model")
    assert "DAHONO" not in _provider_names(dependencies_module._build_copilot_ai_client())


def test_no_registration_without_model(monkeypatch, dependencies_module):
    monkeypatch.setenv("AI5R_DAHONO_API_KEY", FAKE_KEY)
    assert "DAHONO" not in _provider_names(dependencies_module._build_copilot_ai_client())


def test_direct_providers_unaffected(monkeypatch, dependencies_module):
    assert _provider_names(dependencies_module._build_copilot_ai_client()) == ["OLLAMA"]
    monkeypatch.setenv("AI5R_CLAUDE_API_KEY", FAKE_KEY)
    _configured(monkeypatch)
    names = _provider_names(dependencies_module._build_copilot_ai_client())
    assert names == ["CLAUDE", "OLLAMA", "DAHONO"]


def test_dahono_is_never_automatic_primary(monkeypatch, dependencies_module):
    monkeypatch.setenv("AI5R_CLAUDE_API_KEY", FAKE_KEY)
    _configured(monkeypatch)
    router = dependencies_module._build_copilot_ai_client()._router
    for provider in router.provider_registry.list_all():
        provider.health = lambda p=provider: type(
            "H", (), {"healthy": True, "provider": p.provider_name, "detail": ""}
        )()
    request = LLMRequest(prompt="hello")
    for capability in ("chat", "coding", "reasoning", "summarization", "translation"):
        ordered = router._ordered_candidates(capability, request)
        assert ordered[-1].provider_name == "DAHONO"
        if len(ordered) > 1:  # sole candidate (e.g. translation) is not "preferred"
            assert ordered[0].provider_name != "DAHONO"


def test_zero_cost_alone_does_not_prefer_dahono():
    router = Router()
    router.register_provider(ClaudeProvider())
    router.register_provider(OllamaProvider())
    dahono = DahonoProvider(OpenAICompatibleConfig(api_key="k", model="m"))
    router.register_provider(dahono)
    assert dahono.estimate_cost(LLMRequest(prompt="x")).estimated_usd == 0.0
    ordered = router._ordered_candidates("chat", LLMRequest(prompt="x"))
    assert ordered[0].provider_name == "CLAUDE"

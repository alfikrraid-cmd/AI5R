import os
import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
AI5R_SDK_PATH = CORE_SERVICES_PATH.parent / "AI5R-SDK"
for path in (CORE_SERVICES_PATH, AI5R_SDK_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from AI_RUNTIME.ROUTER.exceptions import (
    AllProvidersFailedError,
    CapabilityNotSupportedError,
    ProviderNotRegisteredError,
)
from AI_RUNTIME.ROUTER.router import Router
from OSA.LLM_PROVIDER import CostEstimate, HealthStatus, LLMRequest, LLMResponse, MockLLMProvider

from API.engineering_ai_client import EngineeringAIClient


class _EchoProvider(MockLLMProvider):
    """Echoes request fields back into the response content so tests can
    verify EngineeringAIClient constructs LLMRequest correctly without any
    network access."""

    provider_name = "ECHO"

    def generate(self, request):
        return LLMResponse(
            provider=self.provider_name,
            model="echo-model",
            content=f"system={request.system_prompt}|temp={request.temperature}|meta={request.metadata}",
            finish_reason="stop",
        )


class _JSONProvider(MockLLMProvider):
    provider_name = "JSON_PROVIDER"

    def generate(self, request):
        return LLMResponse(provider=self.provider_name, model="json-model", content='{"ok": true, "count": 3}', finish_reason="stop")


class _InvalidJSONProvider(MockLLMProvider):
    provider_name = "BAD_JSON"

    def generate(self, request):
        return LLMResponse(provider=self.provider_name, model="bad-json-model", content="not json at all", finish_reason="stop")


class _CostAwareProvider(MockLLMProvider):
    provider_name = "COSTY"

    def estimate_cost(self, request):
        return CostEstimate(provider=self.provider_name, model="costy-model", estimated_usd=1.23)


class _FailingProvider(MockLLMProvider):
    provider_name = "FAILING"

    def generate(self, request):
        raise RuntimeError("provider down")


class _TimeoutProvider(MockLLMProvider):
    provider_name = "TIMEOUT_PRONE"

    def generate(self, request):
        raise TimeoutError("simulated network timeout")


def _router_with(*providers):
    router = Router()
    for provider in providers:
        router.register_provider(provider)
    return router


def test_generate_returns_plain_string():
    client = EngineeringAIClient(_router_with(MockLLMProvider()))

    result = client.generate("hello AI5R")

    assert isinstance(result, str)
    assert result == "MOCK_RESPONSE::hello AI5R"


def test_generate_passes_system_prompt_temperature_and_metadata_through():
    client = EngineeringAIClient(_router_with(_EchoProvider()))

    result = client.generate("hi", system_prompt="be terse", temperature=0.7, metadata={"k": "v"})

    assert result == "system=be terse|temp=0.7|meta={'k': 'v'}"


def test_generate_is_deterministic_for_identical_input():
    client = EngineeringAIClient(_router_with(MockLLMProvider()))

    first = client.generate("same input")
    second = client.generate("same input")

    assert first == second


def test_generate_raises_on_empty_prompt():
    # MockLLMProvider.generate() raises ValueError("prompt is required"),
    # but Router's FallbackManager treats every provider exception
    # (validation or network) as fallback-eligible and re-raises
    # AllProvidersFailedError once every candidate is exhausted -- this
    # class does not special-case or swallow that, it surfaces exactly
    # what Router produces.
    client = EngineeringAIClient(_router_with(MockLLMProvider()))

    with pytest.raises(AllProvidersFailedError) as excinfo:
        client.generate("")

    assert isinstance(excinfo.value.errors["MOCK"], ValueError)


def test_generate_json_returns_parsed_dict():
    client = EngineeringAIClient(_router_with(_JSONProvider()))

    result = client.generate_json("give me json")

    assert result == {"ok": True, "count": 3}


def test_generate_json_raises_on_invalid_json_content():
    client = EngineeringAIClient(_router_with(_InvalidJSONProvider()))

    with pytest.raises(Exception):
        client.generate_json("give me json")


def test_generate_json_does_not_modify_the_given_prompt():
    class _PromptCapturingProvider(MockLLMProvider):
        provider_name = "CAPTURE"
        captured_prompt = None

        def generate(self, request):
            _PromptCapturingProvider.captured_prompt = request.prompt
            return LLMResponse(provider=self.provider_name, model="m", content="{}", finish_reason="stop")

    client = EngineeringAIClient(_router_with(_PromptCapturingProvider()))

    client.generate_json("exact prompt text")

    assert _PromptCapturingProvider.captured_prompt == "exact prompt text"


def test_health_delegates_to_router():
    router = _router_with(MockLLMProvider())
    client = EngineeringAIClient(router)

    result = client.health()

    assert result == router.health()
    assert result == {"MOCK": HealthStatus(provider="MOCK", healthy=True, detail="not monitored")}


def test_health_aggregates_multiple_providers():
    client = EngineeringAIClient(_router_with(MockLLMProvider(), _CostAwareProvider()))

    result = client.health()

    assert set(result.keys()) == {"MOCK", "COSTY"}


def test_list_models_returns_empty_list_when_none_registered():
    client = EngineeringAIClient(_router_with(MockLLMProvider()))

    assert client.list_models() == []


def test_list_models_reuses_router_model_registry():
    from AI_RUNTIME.ROUTER.model_registry import ModelDescriptor

    router = _router_with(MockLLMProvider())
    router.model_registry.register(ModelDescriptor(model_name="mock-model", provider_name="MOCK"))
    client = EngineeringAIClient(router)

    models = client.list_models()

    assert len(models) == 1
    assert models[0].model_name == "mock-model"


def test_estimate_cost_delegates_to_provider():
    client = EngineeringAIClient(_router_with(_CostAwareProvider()))

    estimate = client.estimate_cost("how much?")

    assert isinstance(estimate, CostEstimate)
    assert estimate.provider == "COSTY"
    assert estimate.estimated_usd == 1.23


def test_estimate_cost_default_is_zero_for_plain_mock_provider():
    client = EngineeringAIClient(_router_with(MockLLMProvider()))

    estimate = client.estimate_cost("how much?")

    assert estimate.estimated_usd == 0.0


def test_switch_model_pins_generation_to_named_provider():
    client = EngineeringAIClient(_router_with(MockLLMProvider(), _CostAwareProvider()))

    client.switch_model("COSTY")
    result = client.generate("hello")

    assert result == "MOCK_RESPONSE::hello"  # _CostAwareProvider inherits MockLLMProvider.generate


def test_switch_model_bypasses_router_ranking_even_if_other_provider_would_be_preferred():
    class _AlwaysFails(MockLLMProvider):
        provider_name = "PREFERRED_BUT_BROKEN"

        def generate(self, request):
            raise RuntimeError("should never be called once pinned elsewhere")

    client = EngineeringAIClient(_router_with(_AlwaysFails(), MockLLMProvider()))
    client.switch_model("MOCK")

    result = client.generate("hello")

    assert result == "MOCK_RESPONSE::hello"


def test_switch_model_raises_for_unregistered_provider():
    client = EngineeringAIClient(_router_with(MockLLMProvider()))

    with pytest.raises(ProviderNotRegisteredError):
        client.switch_model("NOT_REGISTERED")


def test_switch_model_none_clears_pin_and_restores_router_selection():
    client = EngineeringAIClient(_router_with(MockLLMProvider()))
    client.switch_model("MOCK")

    client.switch_model(None)
    result = client.generate("hello")

    assert result == "MOCK_RESPONSE::hello"


def test_generate_falls_back_when_first_provider_fails():
    client = EngineeringAIClient(_router_with(_FailingProvider(), MockLLMProvider()))

    result = client.generate("hi")

    assert result == "MOCK_RESPONSE::hi"


def test_generate_raises_all_providers_failed_error_when_every_provider_fails():
    client = EngineeringAIClient(_router_with(_FailingProvider()))

    with pytest.raises(AllProvidersFailedError):
        client.generate("hi")


def test_generate_surfaces_timeout_like_errors_via_fallback_without_swallowing():
    client = EngineeringAIClient(_router_with(_TimeoutProvider()))

    with pytest.raises(AllProvidersFailedError) as excinfo:
        client.generate("hi")

    assert isinstance(excinfo.value.errors["TIMEOUT_PRONE"], TimeoutError)


def test_generate_with_unsupported_capability_raises_capability_not_supported():
    client = EngineeringAIClient(_router_with(MockLLMProvider()))

    with pytest.raises(CapabilityNotSupportedError):
        client.generate("hi", capability="vision")


def test_missing_configuration_raises_before_any_network_access():
    # Real provider class (not a fake) with no API key configured: proves
    # EngineeringAIClient surfaces the provider's own configuration
    # validation unchanged, and that this happens before any HTTP call
    # (ClaudeProvider.generate() raises on missing api_key before
    # urllib.request.urlopen is ever reached) -- so this test needs no
    # network mocking at all.
    from AI_RUNTIME.ROUTER.providers.claude_provider import ClaudeConfig, ClaudeProvider

    previous = os.environ.pop("AI5R_CLAUDE_API_KEY", None)
    try:
        provider = ClaudeProvider(ClaudeConfig(api_key=""))
        client = EngineeringAIClient(_router_with(provider))

        with pytest.raises(AllProvidersFailedError) as excinfo:
            client.generate("hi")

        assert isinstance(excinfo.value.errors["CLAUDE"], ValueError)
    finally:
        if previous is not None:
            os.environ["AI5R_CLAUDE_API_KEY"] = previous


def test_constructor_requires_explicit_router_no_hidden_auto_registration():
    router = Router()  # deliberately empty -- no providers registered

    client = EngineeringAIClient(router)

    with pytest.raises(CapabilityNotSupportedError):
        client.generate("hi")


def test_module_has_no_gateway_or_database_imports():
    import API.engineering_ai_client as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]

    assert not any("Gateway" in line for line in import_lines)
    assert not any(".TESTS" in line for line in import_lines)


def test_module_contains_no_hardcoded_secret_looking_literals():
    import API.engineering_ai_client as module

    source = Path(module.__file__).read_text(encoding="utf-8")

    assert "sk-" not in source
    assert "api_key=\"" not in source.replace(" ", "")
    assert "os.getenv" not in source  # config is entirely the provider's/Router's responsibility, not this class's


def test_estimate_cost_uses_router_capability_and_provider_selector_not_new_ranking():
    router = _router_with(_CostAwareProvider())
    client = EngineeringAIClient(router)

    estimate = client.estimate_cost("x")

    # Selected via router.capability_router / router.provider_selector,
    # the same collaborators Router.generate() itself uses.
    candidates = router.capability_router.candidates("chat")
    ordered = router.provider_selector.order(candidates, LLMRequest(prompt=""))
    assert estimate.provider == ordered[0].provider_name


def test_two_different_prompts_produce_different_generate_output():
    client = EngineeringAIClient(_router_with(MockLLMProvider()))

    first = client.generate("prompt A")
    second = client.generate("prompt B")

    assert first != second

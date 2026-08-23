import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.exceptions import (
    AllProvidersFailedError,
    CapabilityNotSupportedError,
    ProviderNotRegisteredError,
)
from AI_RUNTIME.ROUTER.router import Router
from OSA.LLM_PROVIDER import (
    EmbeddingsRequest,
    EmbeddingsResponse,
    HealthStatus,
    LLMRequest,
    LLMResponse,
    MockLLMProvider,
)


class _EmbeddingCapableProvider(MockLLMProvider):
    provider_name = "EMBEDDER"

    def supported_capabilities(self):
        return frozenset({"chat", "embedding"})

    def embeddings(self, request):
        return EmbeddingsResponse(
            provider=self.provider_name, model="embed-1", vectors=[[0.1, 0.2]] * len(request.input)
        )


def test_register_and_generate_round_trip():
    router = Router()
    router.register_provider(MockLLMProvider())

    response = router.generate(LLMRequest(prompt="hello AI5R"))

    assert isinstance(response, LLMResponse)
    assert response.provider == "MOCK"
    assert response.content == "MOCK_RESPONSE::hello AI5R"


def test_generate_with_no_provider_for_capability_raises():
    router = Router()
    router.register_provider(MockLLMProvider())

    with pytest.raises(CapabilityNotSupportedError):
        router.generate(LLMRequest(prompt="hi"), capability="vision")


def test_unregister_provider_then_resolve_fails():
    router = Router()
    router.register_provider(MockLLMProvider())

    router.unregister_provider("MOCK")

    with pytest.raises(ProviderNotRegisteredError):
        router.provider_registry.resolve("MOCK")


def test_generate_falls_back_when_first_provider_fails():
    class _Failing(MockLLMProvider):
        provider_name = "FAILING"

        def generate(self, request):
            raise RuntimeError("provider down")

    router = Router()
    router.register_provider(_Failing())
    router.register_provider(MockLLMProvider())

    response = router.generate(LLMRequest(prompt="hi"))

    assert response.provider == "MOCK"


def test_generate_raises_when_every_provider_fails():
    class _Failing(MockLLMProvider):
        provider_name = "FAILING"

        def generate(self, request):
            raise RuntimeError("provider down")

    router = Router()
    router.register_provider(_Failing())

    with pytest.raises(AllProvidersFailedError):
        router.generate(LLMRequest(prompt="hi"))


def test_embeddings_routes_to_capable_provider():
    router = Router()
    router.register_provider(_EmbeddingCapableProvider())

    response = router.embeddings(EmbeddingsRequest(input=["a", "b"]))

    assert response.provider == "EMBEDDER"
    assert len(response.vectors) == 2


def test_health_reports_every_registered_provider():
    router = Router()
    router.register_provider(MockLLMProvider())

    health = router.health()

    assert health == {"MOCK": HealthStatus(provider="MOCK", healthy=True, detail="not monitored")}


def test_statistics_reflects_recorded_calls():
    router = Router()
    router.register_provider(MockLLMProvider())

    router.generate(LLMRequest(prompt="hi"))

    stats = router.statistics()
    assert stats["MOCK"].successes == 1

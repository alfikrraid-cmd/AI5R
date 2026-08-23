from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(slots=True)
class LLMRequest:
    prompt: str
    system_prompt: str = ""
    temperature: float = 0.2
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class LLMResponse:
    provider: str
    model: str
    content: str
    finish_reason: str


@dataclass(slots=True)
class StreamChunk:
    provider: str
    model: str
    delta: str
    finish_reason: str | None = None


@dataclass(slots=True)
class EmbeddingsRequest:
    input: list[str]
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class EmbeddingsResponse:
    provider: str
    model: str
    vectors: list[list[float]]


@dataclass(slots=True)
class HealthStatus:
    provider: str
    healthy: bool
    detail: str = ""


@dataclass(slots=True)
class CostEstimate:
    provider: str
    model: str
    estimated_usd: float


class BaseLLMProvider(ABC):
    """Canonical provider interface (AI_RUNTIME/ROUTER evolution, MWO pending).

    ``generate`` remains the sole required method — every capability added
    below has a safe, non-abstract default so existing concrete providers
    (``MockLLMProvider``, ``OpenAICompatibleProvider``) continue to
    instantiate and behave exactly as before without overriding anything.
    """

    provider_name: str = "BASE"

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError

    def stream(self, request: LLMRequest) -> Iterator[StreamChunk]:
        raise NotImplementedError(f"{self.provider_name} does not support stream()")

    def embeddings(self, request: EmbeddingsRequest) -> EmbeddingsResponse:
        raise NotImplementedError(f"{self.provider_name} does not support embeddings()")

    def health(self) -> HealthStatus:
        return HealthStatus(provider=self.provider_name, healthy=True, detail="not monitored")

    def estimate_cost(self, request: LLMRequest) -> CostEstimate:
        return CostEstimate(provider=self.provider_name, model="", estimated_usd=0.0)

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"chat"})


class MockLLMProvider(BaseLLMProvider):
    provider_name = "MOCK"

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.prompt:
            raise ValueError("prompt is required")

        return LLMResponse(
            provider=self.provider_name,
            model="mock-model",
            content=f"MOCK_RESPONSE::{request.prompt}",
            finish_reason="stop",
        )


class LLMProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}

    def register(self, provider: BaseLLMProvider):
        self._providers[provider.provider_name] = provider

    def resolve(self, provider_name: str) -> BaseLLMProvider:
        if provider_name not in self._providers:
            raise ValueError("provider is not registered")
        return self._providers[provider_name]

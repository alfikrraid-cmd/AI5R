from __future__ import annotations

from typing import Iterator

from OSA.LLM_PROVIDER import (
    BaseLLMProvider,
    EmbeddingsRequest,
    EmbeddingsResponse,
    HealthStatus,
    LLMRequest,
    LLMResponse,
    StreamChunk,
)

from .capability_router import CapabilityRouter
from .cost_policy import CostPolicy
from .fallback_manager import FallbackManager
from .metrics import Metrics, ProviderStats
from .model_registry import ModelRegistry
from .provider_registry import ProviderRegistry
from .provider_selector import ProviderSelector
from .retry_policy import RetryPolicy


class Router:
    """Enterprise provider-agnostic AI Router. The single entry point every
    module SHALL call instead of talking to a provider directly.

    All collaborators are injected (constructor DI) with sensible defaults,
    so callers may override any stage (e.g. a stricter CostPolicy) without
    subclassing Router itself.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_registry: ModelRegistry | None = None,
        capability_router: CapabilityRouter | None = None,
        provider_selector: ProviderSelector | None = None,
        fallback_manager: FallbackManager | None = None,
        cost_policy: CostPolicy | None = None,
        retry_policy: RetryPolicy | None = None,
        metrics: Metrics | None = None,
    ):
        self.metrics = metrics or Metrics()
        self.cost_policy = cost_policy or CostPolicy()
        self.retry_policy = retry_policy or RetryPolicy()
        self.provider_registry = provider_registry or ProviderRegistry()
        self.model_registry = model_registry or ModelRegistry()
        self.capability_router = capability_router or CapabilityRouter(self.provider_registry)
        self.provider_selector = provider_selector or ProviderSelector(
            cost_policy=self.cost_policy, metrics=self.metrics
        )
        self.fallback_manager = fallback_manager or FallbackManager(
            retry_policy=self.retry_policy, metrics=self.metrics
        )

    # -- registration -----------------------------------------------------

    def register_provider(self, provider: BaseLLMProvider) -> None:
        self.provider_registry.register(provider)

    def unregister_provider(self, provider_name: str) -> None:
        self.provider_registry.unregister(provider_name)

    # -- routing pipeline ---------------------------------------------------

    def _ordered_candidates(self, capability: str, request: LLMRequest) -> list[BaseLLMProvider]:
        candidates = self.capability_router.candidates(capability)
        return self.provider_selector.order(candidates, request)

    # -- public API ---------------------------------------------------------

    def generate(self, request: LLMRequest, capability: str = "chat") -> LLMResponse:
        ordered = self._ordered_candidates(capability, request)
        return self.fallback_manager.execute(ordered, lambda provider: provider.generate(request))

    def stream(self, request: LLMRequest, capability: str = "chat") -> Iterator[StreamChunk]:
        ordered = self._ordered_candidates(capability, request)
        return self.fallback_manager.execute(ordered, lambda provider: provider.stream(request))

    def embeddings(
        self, request: EmbeddingsRequest, capability: str = "embedding"
    ) -> EmbeddingsResponse:
        candidates = self.capability_router.candidates(capability)
        ordered = self.provider_selector.order(candidates, LLMRequest(prompt=""))
        return self.fallback_manager.execute(ordered, lambda provider: provider.embeddings(request))

    def health(self) -> dict[str, HealthStatus]:
        return {
            provider.provider_name: provider.health()
            for provider in self.provider_registry.list_all()
        }

    def statistics(self) -> dict[str, ProviderStats]:
        return self.metrics.snapshot()

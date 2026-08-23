from __future__ import annotations

from dataclasses import dataclass

from OSA.LLM_PROVIDER import BaseLLMProvider, LLMRequest


@dataclass(slots=True)
class CostPolicy:
    """Cost stage of the routing pipeline: budget filtering + cheapest-first ranking."""

    max_cost_usd: float | None = None

    def is_within_budget(self, provider: BaseLLMProvider, request: LLMRequest) -> bool:
        if self.max_cost_usd is None:
            return True
        return provider.estimate_cost(request).estimated_usd <= self.max_cost_usd

    def rank(
        self, providers: list[BaseLLMProvider], request: LLMRequest
    ) -> list[BaseLLMProvider]:
        return sorted(providers, key=lambda p: p.estimate_cost(request).estimated_usd)

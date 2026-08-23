from __future__ import annotations

from typing import Callable

from OSA.LLM_PROVIDER import BaseLLMProvider, LLMRequest

from .cost_policy import CostPolicy
from .exceptions import NoProviderAvailableError
from .metrics import Metrics

Policy = Callable[[BaseLLMProvider, LLMRequest], bool]


class ProviderSelector:
    """Selects, from a capability-filtered candidate list, the ordered
    preference of providers to try, per the routing pipeline:

    Capability (upstream, CapabilityRouter) -> Health -> Cost -> Latency ->
    Policy -> Availability.

    Returns every surviving candidate in preference order (not just the
    winner) so FallbackManager can walk the rest on failure.
    """

    def __init__(
        self,
        cost_policy: CostPolicy | None = None,
        metrics: Metrics | None = None,
        policies: list[Policy] | None = None,
        max_consecutive_failures: int = 3,
    ):
        self._cost_policy = cost_policy or CostPolicy()
        self._metrics = metrics or Metrics()
        self._policies = policies or []
        self._max_consecutive_failures = max_consecutive_failures

    def order(
        self, candidates: list[BaseLLMProvider], request: LLMRequest
    ) -> list[BaseLLMProvider]:
        # Health
        healthy = [p for p in candidates if p.health().healthy]
        if not healthy:
            raise NoProviderAvailableError("no healthy provider available")

        # Cost: prefer providers within budget, cheapest first; if the
        # budget excludes everyone, fall back to the full healthy pool
        # rather than failing outright (Policy stage may still exclude them).
        within_budget = [
            p for p in healthy if self._cost_policy.is_within_budget(p, request)
        ]
        cost_pool = within_budget or healthy
        ranked = self._cost_policy.rank(cost_pool, request)

        # Latency: stable-sort by observed average latency (0.0 for unseen providers)
        ranked = sorted(ranked, key=lambda p: self._metrics.average_latency(p.provider_name))

        # Policy: injectable custom predicates (enterprise rules, allow/deny, etc.)
        for policy in self._policies:
            ranked = [p for p in ranked if policy(p, request)]

        # Availability: exclude providers currently tripped by repeated failures
        available = [
            p
            for p in ranked
            if self._metrics.is_available(p.provider_name, self._max_consecutive_failures)
        ]

        if not available:
            raise NoProviderAvailableError("no available provider survived routing")

        return available

    def select(self, candidates: list[BaseLLMProvider], request: LLMRequest) -> BaseLLMProvider:
        return self.order(candidates, request)[0]

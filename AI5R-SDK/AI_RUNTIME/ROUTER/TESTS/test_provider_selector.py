import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.cost_policy import CostPolicy
from AI_RUNTIME.ROUTER.exceptions import NoProviderAvailableError
from AI_RUNTIME.ROUTER.metrics import Metrics
from AI_RUNTIME.ROUTER.provider_selector import ProviderSelector
from OSA.LLM_PROVIDER import CostEstimate, HealthStatus, LLMRequest, MockLLMProvider

REQUEST = LLMRequest(prompt="hello")


class _Provider(MockLLMProvider):
    def __init__(self, name, *, healthy=True, cost=0.0):
        self.provider_name = name
        self._healthy = healthy
        self._cost = cost

    def health(self):
        return HealthStatus(provider=self.provider_name, healthy=self._healthy)

    def estimate_cost(self, request):
        return CostEstimate(provider=self.provider_name, model="m", estimated_usd=self._cost)


def test_select_returns_only_healthy_provider():
    healthy = _Provider("HEALTHY", healthy=True)
    unhealthy = _Provider("UNHEALTHY", healthy=False)
    selector = ProviderSelector()

    assert selector.select([unhealthy, healthy], REQUEST) is healthy


def test_select_raises_when_no_provider_healthy():
    selector = ProviderSelector()
    unhealthy = _Provider("UNHEALTHY", healthy=False)

    with pytest.raises(NoProviderAvailableError):
        selector.select([unhealthy], REQUEST)


def test_select_prefers_cheaper_provider():
    selector = ProviderSelector(cost_policy=CostPolicy())
    cheap = _Provider("CHEAP", cost=0.001)
    expensive = _Provider("EXPENSIVE", cost=1.0)

    assert selector.select([expensive, cheap], REQUEST) is cheap


def test_select_prefers_lower_latency_when_cost_equal():
    metrics = Metrics()
    metrics.record_success("SLOW", latency_seconds=5.0)
    metrics.record_success("FAST", latency_seconds=0.1)
    selector = ProviderSelector(metrics=metrics)
    slow = _Provider("SLOW", cost=0.0)
    fast = _Provider("FAST", cost=0.0)

    assert selector.select([slow, fast], REQUEST) is fast


def test_policy_predicate_excludes_provider():
    denylist = _Provider("DENIED")
    allowed = _Provider("ALLOWED")
    selector = ProviderSelector(policies=[lambda p, r: p.provider_name != "DENIED"])

    assert selector.select([denylist, allowed], REQUEST) is allowed


def test_availability_excludes_provider_tripped_by_consecutive_failures():
    metrics = Metrics()
    metrics.record_failure("FLAKY")
    metrics.record_failure("FLAKY")
    metrics.record_failure("FLAKY")
    selector = ProviderSelector(metrics=metrics, max_consecutive_failures=3)
    flaky = _Provider("FLAKY")
    stable = _Provider("STABLE")

    assert selector.select([flaky, stable], REQUEST) is stable


def test_order_returns_full_fallback_sequence():
    selector = ProviderSelector()
    cheap = _Provider("CHEAP", cost=0.0)
    expensive = _Provider("EXPENSIVE", cost=1.0)

    ordered = selector.order([expensive, cheap], REQUEST)

    assert [p.provider_name for p in ordered] == ["CHEAP", "EXPENSIVE"]


def test_budget_excluding_everyone_falls_back_to_full_healthy_pool():
    selector = ProviderSelector(cost_policy=CostPolicy(max_cost_usd=0.001))
    only_option = _Provider("ONLY_OPTION", cost=5.0)

    assert selector.select([only_option], REQUEST) is only_option

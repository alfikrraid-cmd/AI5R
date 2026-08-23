import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.cost_policy import CostPolicy
from OSA.LLM_PROVIDER import CostEstimate, LLMRequest, MockLLMProvider


class _CostedProvider(MockLLMProvider):
    def __init__(self, provider_name: str, cost_usd: float):
        self.provider_name = provider_name
        self._cost_usd = cost_usd

    def estimate_cost(self, request):
        return CostEstimate(provider=self.provider_name, model="mock-model", estimated_usd=self._cost_usd)


def test_no_budget_means_everything_is_within_budget():
    policy = CostPolicy()
    provider = _CostedProvider("EXPENSIVE", 999.0)

    assert policy.is_within_budget(provider, LLMRequest(prompt="hi")) is True


def test_budget_excludes_provider_over_limit():
    policy = CostPolicy(max_cost_usd=0.01)
    cheap = _CostedProvider("CHEAP", 0.001)
    expensive = _CostedProvider("EXPENSIVE", 1.0)

    assert policy.is_within_budget(cheap, LLMRequest(prompt="hi")) is True
    assert policy.is_within_budget(expensive, LLMRequest(prompt="hi")) is False


def test_rank_orders_cheapest_first():
    policy = CostPolicy()
    cheap = _CostedProvider("CHEAP", 0.001)
    mid = _CostedProvider("MID", 0.01)
    expensive = _CostedProvider("EXPENSIVE", 1.0)

    ranked = policy.rank([expensive, cheap, mid], LLMRequest(prompt="hi"))

    assert [p.provider_name for p in ranked] == ["CHEAP", "MID", "EXPENSIVE"]

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "AI5R-SDK"))
sys.path.insert(0, str(ROOT / "CORE-SERVICES" / "API"))

import pytest

from AI_RUNTIME.ROUTER import providers as provider_pkg
from AI_RUNTIME.ROUTER.exceptions import AllProvidersFailedError, NoProviderAvailableError
from AI_RUNTIME.ROUTER.metrics import Metrics
from AI_RUNTIME.ROUTER.provider_selector import ProviderSelector
from AI_RUNTIME.ROUTER.router import Router
from AI_RUNTIME.ROUTER.routing_policy import (
    PROVIDER_CATEGORIES,
    ProviderCategory,
    RoutingMode,
    RoutingPolicy,
    RoutingPolicyError,
    parse_routing_policy,
)
from engineering_ai_client import EngineeringAIClient
from OSA.LLM_PROVIDER import HealthStatus, LLMRequest, LLMResponse, MockLLMProvider

REQUEST = LLMRequest(prompt="hello")


class _P(MockLLMProvider):
    def __init__(self, name, *, healthy=True, caps=("chat",), fail=False):
        self.provider_name = name
        self._healthy, self._caps, self._fail = healthy, frozenset(caps), fail

    def health(self):
        return HealthStatus(provider=self.provider_name, healthy=self._healthy)

    def supported_capabilities(self):
        return self._caps

    def generate(self, request):
        if self._fail:
            raise RuntimeError("boom")
        return LLMResponse(provider=self.provider_name, model="m", content=self.provider_name, finish_reason="stop")


def _names(providers):
    return [p.provider_name for p in providers]


def _selector(mode, metrics=None):
    return ProviderSelector(metrics=metrics, routing_policy=RoutingPolicy(RoutingMode(mode)))


def _pool():
    # registration order deliberately puts Dahono last and Ollama mid-pack
    return [_P("CLAUDE"), _P("OPENROUTER"), _P("OLLAMA"), _P("GEMINI"), _P("DAHONO")]


# A. parsing
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_or_blank_is_auto(value):
    assert parse_routing_policy(value).mode is RoutingMode.AUTO


@pytest.mark.parametrize("mode", ["AUTO", "DAHONO_PRIMARY", "DIRECT_PRIMARY", "LOCAL_FIRST"])
def test_valid_modes_accepted(mode):
    assert parse_routing_policy(mode).mode.value == mode


@pytest.mark.parametrize("value", ["bogus", "auto", "COST_OPTIMIZED"])
def test_invalid_rejected_including_cost_optimized(value):
    with pytest.raises(RoutingPolicyError):
        parse_routing_policy(value)


# B. AUTO
def test_auto_preserves_baseline_order():
    pool = _pool()
    baseline = _names(ProviderSelector().order(pool, REQUEST))
    assert _names(_selector("AUTO").order(pool, REQUEST)) == baseline
    assert baseline == ["CLAUDE", "OPENROUTER", "OLLAMA", "GEMINI", "DAHONO"]


# C. DAHONO_PRIMARY
def test_dahono_first_and_others_keep_order():
    assert _names(_selector("DAHONO_PRIMARY").order(_pool(), REQUEST)) == [
        "DAHONO", "CLAUDE", "OPENROUTER", "OLLAMA", "GEMINI"]


def test_dahono_unsupported_capability_absent():
    router = Router(provider_selector=_selector("DAHONO_PRIMARY"))
    router.register_provider(_P("CLAUDE", caps=("chat", "vision")))
    router.register_provider(_P("DAHONO", caps=("chat",)))
    assert router.generate(REQUEST, capability="vision").content == "CLAUDE"


def test_dahono_unhealthy_absent():
    pool = [_P("CLAUDE"), _P("DAHONO", healthy=False)]
    assert _names(_selector("DAHONO_PRIMARY").order(pool, REQUEST)) == ["CLAUDE"]


def test_dahono_unavailable_excluded_despite_priority():
    metrics = Metrics()
    for _ in range(3):
        metrics.record_failure("DAHONO", 0.1)
    out = _names(_selector("DAHONO_PRIMARY", metrics).order(_pool(), REQUEST))
    assert "DAHONO" not in out and out[0] == "CLAUDE"


def test_latency_cannot_defeat_dahono_priority_but_orders_fallbacks():
    metrics = Metrics()
    metrics.record_success("DAHONO", 25.0)
    metrics.record_success("CLAUDE", 5.0)
    metrics.record_success("GEMINI", 1.0)
    out = _names(_selector("DAHONO_PRIMARY", metrics).order(_pool(), REQUEST))
    assert out[0] == "DAHONO"
    assert out.index("GEMINI") < out.index("CLAUDE")


# D. DIRECT_PRIMARY
def test_direct_group_first_with_latency_order_inside():
    metrics = Metrics()
    metrics.record_success("GEMINI", 1.0)
    metrics.record_success("CLAUDE", 5.0)
    metrics.record_success("OLLAMA", 0.01)
    out = _names(_selector("DIRECT_PRIMARY", metrics).order(_pool(), REQUEST))
    # Latency stage: unseen (0.0) first, then OLLAMA .01, GEMINI 1, CLAUDE 5 --
    # direct group is lifted to the front preserving GEMINI before CLAUDE.
    assert out[:2] == ["GEMINI", "CLAUDE"]
    assert set(out[2:]) == {"OPENROUTER", "OLLAMA", "DAHONO"}


def test_direct_primary_registration_order_inside_group_preserved():
    out = _names(_selector("DIRECT_PRIMARY").order(_pool(), REQUEST))
    assert out == ["CLAUDE", "GEMINI", "OPENROUTER", "OLLAMA", "DAHONO"]


def test_direct_primary_unclassified_gets_no_priority():
    out = _names(_selector("DIRECT_PRIMARY").order([_P("FUTURE"), _P("CLAUDE")], REQUEST))
    assert out == ["CLAUDE", "FUTURE"]


# E. LOCAL_FIRST
def test_local_first_keeps_cloud_fallback():
    assert _names(_selector("LOCAL_FIRST").order(_pool(), REQUEST)) == [
        "OLLAMA", "CLAUDE", "OPENROUTER", "GEMINI", "DAHONO"]


def test_local_first_unclassified_gets_no_priority():
    out = _names(_selector("LOCAL_FIRST").order([_P("FUTURE"), _P("OLLAMA")], REQUEST))
    assert out == ["OLLAMA", "FUTURE"]


def test_unavailable_local_excluded():
    metrics = Metrics()
    for _ in range(3):
        metrics.record_failure("OLLAMA", 0.1)
    out = _names(_selector("LOCAL_FIRST", metrics).order(_pool(), REQUEST))
    assert "OLLAMA" not in out and out[0] == "CLAUDE"


# F. categories
def test_every_exported_provider_is_classified():
    classes = [getattr(provider_pkg, n) for n in provider_pkg.__all__ if n.endswith("Provider")]
    assert len(classes) == 9
    for cls in classes:
        assert cls.provider_name in PROVIDER_CATEGORIES, cls.__name__


def test_category_assignments():
    c = PROVIDER_CATEGORIES
    assert c["DAHONO"] is ProviderCategory.AGGREGATOR
    assert c["OLLAMA"] is ProviderCategory.LOCAL
    assert c["OPENROUTER"] is ProviderCategory.AGGREGATOR
    assert c["LITELLM"] is ProviderCategory.AGGREGATOR
    for n in ("CLAUDE", "OPENAI", "GEMINI", "DEEPSEEK", "GROK"):
        assert c[n] is ProviderCategory.DIRECT


# G. existing semantics
def test_boolean_policies_still_filter_after_ordering():
    sel = ProviderSelector(
        policies=[lambda p, r: p.provider_name != "DAHONO"],
        routing_policy=RoutingPolicy(RoutingMode.DAHONO_PRIMARY),
    )
    assert "DAHONO" not in _names(sel.order(_pool(), REQUEST))


def test_no_healthy_still_raises():
    with pytest.raises(NoProviderAvailableError):
        _selector("DAHONO_PRIMARY").order([_P("DAHONO", healthy=False)], REQUEST)


def test_fallback_walks_policy_order_unchanged():
    metrics = Metrics()
    router = Router(metrics=metrics, provider_selector=_selector("DAHONO_PRIMARY", metrics))
    router.register_provider(_P("CLAUDE"))
    router.register_provider(_P("DAHONO", fail=True))
    assert router.generate(REQUEST).content == "CLAUDE"
    assert metrics.snapshot()["DAHONO"].failures == 1
    only = Router(metrics=Metrics())
    only.register_provider(_P("DAHONO", fail=True))
    with pytest.raises(AllProvidersFailedError):
        only.generate(REQUEST)


def test_manual_pin_bypasses_routing_policy():
    router = Router(provider_selector=_selector("DAHONO_PRIMARY"))
    router.register_provider(_P("DAHONO"))
    router.register_provider(_P("CLAUDE"))
    client = EngineeringAIClient(router, default_provider="CLAUDE")
    assert client.generate("hi") == "CLAUDE"


def test_registration_order_does_not_defeat_policy():
    for pool in (_pool(), list(reversed(_pool()))):
        assert _names(_selector("DAHONO_PRIMARY").order(pool, REQUEST))[0] == "DAHONO"
        assert _names(_selector("LOCAL_FIRST").order(pool, REQUEST))[0] == "OLLAMA"

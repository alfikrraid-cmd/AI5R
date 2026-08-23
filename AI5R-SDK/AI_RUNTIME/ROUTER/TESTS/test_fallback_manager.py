import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.exceptions import AllProvidersFailedError
from AI_RUNTIME.ROUTER.fallback_manager import FallbackManager
from AI_RUNTIME.ROUTER.metrics import Metrics
from AI_RUNTIME.ROUTER.retry_policy import RetryPolicy
from OSA.LLM_PROVIDER import MockLLMProvider


class _Named(MockLLMProvider):
    def __init__(self, name):
        self.provider_name = name


def test_first_provider_success_short_circuits():
    manager = FallbackManager()
    first = _Named("FIRST")
    second = _Named("SECOND")
    calls: list[str] = []

    def call(provider):
        calls.append(provider.provider_name)
        return f"ok:{provider.provider_name}"

    result = manager.execute([first, second], call)

    assert result == "ok:FIRST"
    assert calls == ["FIRST"]


def test_falls_back_to_next_provider_on_failure():
    manager = FallbackManager()
    failing = _Named("FAILING")
    working = _Named("WORKING")

    def call(provider):
        if provider.provider_name == "FAILING":
            raise RuntimeError("boom")
        return "ok"

    result = manager.execute([failing, working], call)

    assert result == "ok"


def test_all_providers_failing_raises_with_every_error():
    manager = FallbackManager()
    a = _Named("A")
    b = _Named("B")

    def call(provider):
        raise RuntimeError(f"{provider.provider_name} failed")

    with pytest.raises(AllProvidersFailedError) as exc_info:
        manager.execute([a, b], call)

    assert set(exc_info.value.errors.keys()) == {"A", "B"}


def test_retry_policy_retries_before_falling_back():
    manager = FallbackManager(retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0))
    flaky = _Named("FLAKY")
    attempts = {"count": 0}

    def call(provider):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("still failing")
        return "recovered"

    result = manager.execute([flaky], call)

    assert result == "recovered"
    assert attempts["count"] == 3


def test_records_metrics_on_success_and_failure():
    metrics = Metrics()
    manager = FallbackManager(metrics=metrics)
    failing = _Named("FAILING")
    working = _Named("WORKING")

    def call(provider):
        if provider.provider_name == "FAILING":
            raise RuntimeError("boom")
        return "ok"

    manager.execute([failing, working], call)

    snapshot = metrics.snapshot()
    assert snapshot["FAILING"].failures == 1
    assert snapshot["WORKING"].successes == 1

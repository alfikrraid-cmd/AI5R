import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.metrics import Metrics


def test_unknown_provider_defaults():
    metrics = Metrics()

    assert metrics.average_latency("UNKNOWN") == 0.0
    assert metrics.success_rate("UNKNOWN") == 1.0
    assert metrics.is_available("UNKNOWN") is True


def test_record_success_updates_stats():
    metrics = Metrics()

    metrics.record_success("OPENAI", latency_seconds=1.0, cost_usd=0.02)
    metrics.record_success("OPENAI", latency_seconds=3.0, cost_usd=0.04)

    stats = metrics.snapshot()["OPENAI"]
    assert stats.calls == 2
    assert stats.successes == 2
    assert stats.failures == 0
    assert stats.total_cost_usd == 0.06
    assert metrics.average_latency("OPENAI") == 2.0


def test_record_failure_updates_consecutive_failures():
    metrics = Metrics()

    metrics.record_failure("CLAUDE")
    metrics.record_failure("CLAUDE")

    stats = metrics.snapshot()["CLAUDE"]
    assert stats.failures == 2
    assert stats.consecutive_failures == 2


def test_success_resets_consecutive_failures():
    metrics = Metrics()
    metrics.record_failure("CLAUDE")
    metrics.record_failure("CLAUDE")

    metrics.record_success("CLAUDE")

    assert metrics.snapshot()["CLAUDE"].consecutive_failures == 0


def test_is_available_false_after_threshold_consecutive_failures():
    metrics = Metrics()

    metrics.record_failure("GEMINI")
    metrics.record_failure("GEMINI")
    metrics.record_failure("GEMINI")

    assert metrics.is_available("GEMINI", max_consecutive_failures=3) is False
    assert metrics.is_available("GEMINI", max_consecutive_failures=4) is True


def test_success_rate_computed_from_calls():
    metrics = Metrics()
    metrics.record_success("OPENAI")
    metrics.record_success("OPENAI")
    metrics.record_failure("OPENAI")

    assert metrics.success_rate("OPENAI") == 2 / 3

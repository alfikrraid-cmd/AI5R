from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProviderStats:
    calls: int = 0
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    total_latency_seconds: float = 0.0
    total_cost_usd: float = 0.0


class Metrics:
    """Per-provider call statistics feeding the Latency and Availability
    routing stages, and the Router.statistics() public API."""

    def __init__(self) -> None:
        self._stats: dict[str, ProviderStats] = {}

    def _stats_for(self, provider_name: str) -> ProviderStats:
        return self._stats.setdefault(provider_name, ProviderStats())

    def record_success(
        self, provider_name: str, latency_seconds: float = 0.0, cost_usd: float = 0.0
    ) -> None:
        stats = self._stats_for(provider_name)
        stats.calls += 1
        stats.successes += 1
        stats.consecutive_failures = 0
        stats.total_latency_seconds += latency_seconds
        stats.total_cost_usd += cost_usd

    def record_failure(self, provider_name: str, latency_seconds: float = 0.0) -> None:
        stats = self._stats_for(provider_name)
        stats.calls += 1
        stats.failures += 1
        stats.consecutive_failures += 1
        stats.total_latency_seconds += latency_seconds

    def average_latency(self, provider_name: str) -> float:
        stats = self._stats.get(provider_name)
        if not stats or stats.calls == 0:
            return 0.0
        return stats.total_latency_seconds / stats.calls

    def success_rate(self, provider_name: str) -> float:
        stats = self._stats.get(provider_name)
        if not stats or stats.calls == 0:
            return 1.0
        return stats.successes / stats.calls

    def is_available(self, provider_name: str, max_consecutive_failures: int = 3) -> bool:
        stats = self._stats.get(provider_name)
        if not stats:
            return True
        return stats.consecutive_failures < max_consecutive_failures

    def snapshot(self) -> dict[str, ProviderStats]:
        return dict(self._stats)

from __future__ import annotations

import time
from typing import Callable, TypeVar

from OSA.LLM_PROVIDER import BaseLLMProvider

from .exceptions import AllProvidersFailedError
from .metrics import Metrics
from .retry_policy import RetryPolicy

T = TypeVar("T")


class FallbackManager:
    """Executes ``call`` against an ordered provider list, retrying each
    provider per RetryPolicy before automatically falling back to the next
    candidate. Records every attempt's outcome/latency to Metrics."""

    def __init__(
        self,
        retry_policy: RetryPolicy | None = None,
        metrics: Metrics | None = None,
    ):
        self._retry_policy = retry_policy or RetryPolicy()
        self._metrics = metrics or Metrics()

    def execute(
        self,
        ordered_providers: list[BaseLLMProvider],
        call: Callable[[BaseLLMProvider], T],
    ) -> T:
        errors: dict[str, Exception] = {}

        for provider in ordered_providers:
            attempt = 0
            while True:
                attempt += 1
                start = time.monotonic()
                try:
                    result = call(provider)
                except Exception as exc:  # noqa: BLE001 - provider failures are all fallback-eligible
                    latency = time.monotonic() - start
                    self._metrics.record_failure(provider.provider_name, latency)
                    if self._retry_policy.should_retry(attempt):
                        time.sleep(self._retry_policy.delay_seconds(attempt))
                        continue
                    errors[provider.provider_name] = exc
                    break
                else:
                    latency = time.monotonic() - start
                    self._metrics.record_success(provider.provider_name, latency)
                    return result

        raise AllProvidersFailedError(errors)

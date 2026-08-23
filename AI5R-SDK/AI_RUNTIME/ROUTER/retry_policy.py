from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RetryPolicy:
    """Per-provider retry behaviour used by FallbackManager before moving on
    to the next candidate."""

    max_attempts: int = 1
    backoff_seconds: float = 0.0

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts

    def delay_seconds(self, attempt: int) -> float:
        return self.backoff_seconds * attempt

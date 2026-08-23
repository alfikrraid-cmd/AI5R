import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.retry_policy import RetryPolicy


def test_default_is_single_attempt_no_retry():
    policy = RetryPolicy()

    assert policy.should_retry(1) is False


def test_should_retry_true_while_under_max_attempts():
    policy = RetryPolicy(max_attempts=3)

    assert policy.should_retry(1) is True
    assert policy.should_retry(2) is True
    assert policy.should_retry(3) is False


def test_delay_seconds_scales_with_attempt_and_backoff():
    policy = RetryPolicy(max_attempts=3, backoff_seconds=0.5)

    assert policy.delay_seconds(1) == 0.5
    assert policy.delay_seconds(2) == 1.0


def test_zero_backoff_means_zero_delay():
    policy = RetryPolicy(max_attempts=3, backoff_seconds=0.0)

    assert policy.delay_seconds(5) == 0.0

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from AI_RUNTIME.ROUTER.exceptions import (
    AllProvidersFailedError,
    BudgetExceededError,
    CapabilityNotSupportedError,
    ModelNotRegisteredError,
    NoProviderAvailableError,
    ProviderAlreadyRegisteredError,
    ProviderNotRegisteredError,
    RouterError,
)


def test_all_router_exceptions_are_router_error():
    for exc_type in (
        ProviderNotRegisteredError,
        ProviderAlreadyRegisteredError,
        ModelNotRegisteredError,
        CapabilityNotSupportedError,
        NoProviderAvailableError,
        BudgetExceededError,
        AllProvidersFailedError,
    ):
        assert issubclass(exc_type, RouterError)


def test_all_providers_failed_error_message_lists_provider_names():
    error = AllProvidersFailedError({"OPENAI": ValueError("boom"), "CLAUDE": TimeoutError("slow")})

    assert "OPENAI" in str(error)
    assert "CLAUDE" in str(error)
    assert error.errors["OPENAI"].args == ("boom",)

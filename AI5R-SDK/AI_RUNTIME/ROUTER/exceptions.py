from __future__ import annotations


class RouterError(Exception):
    """Base exception for every AI_RUNTIME/ROUTER failure."""


class ProviderNotRegisteredError(RouterError):
    pass


class ProviderAlreadyRegisteredError(RouterError):
    pass


class ModelNotRegisteredError(RouterError):
    pass


class CapabilityNotSupportedError(RouterError):
    pass


class NoProviderAvailableError(RouterError):
    pass


class BudgetExceededError(RouterError):
    pass


class AllProvidersFailedError(RouterError):
    def __init__(self, errors: dict[str, Exception]):
        self.errors = errors
        provider_names = ", ".join(errors) or "<none>"
        super().__init__(f"all candidate providers failed: {provider_names}")

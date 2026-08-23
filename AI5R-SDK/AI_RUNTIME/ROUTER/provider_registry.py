from __future__ import annotations

from OSA.LLM_PROVIDER import BaseLLMProvider, LLMProviderRegistry

from .exceptions import ProviderAlreadyRegisteredError, ProviderNotRegisteredError


class ProviderRegistry(LLMProviderRegistry):
    """Evolution of ``OSA.LLM_PROVIDER.LLMProviderRegistry``.

    Inherits ``register``/``resolve`` unchanged (existing OSA consumers keep
    working against the base class without modification) and adds
    unregistration, enumeration, and capability-aware lookup on top of the
    same ``_providers`` storage — no second provider registry is introduced.
    """

    def register(self, provider: BaseLLMProvider, *, allow_replace: bool = True) -> None:
        if not allow_replace and provider.provider_name in self._providers:
            raise ProviderAlreadyRegisteredError(
                f"provider '{provider.provider_name}' is already registered"
            )
        super().register(provider)

    def unregister(self, provider_name: str) -> None:
        if provider_name not in self._providers:
            raise ProviderNotRegisteredError(f"provider '{provider_name}' is not registered")
        del self._providers[provider_name]

    def resolve(self, provider_name: str) -> BaseLLMProvider:
        if provider_name not in self._providers:
            raise ProviderNotRegisteredError(f"provider '{provider_name}' is not registered")
        return self._providers[provider_name]

    def list_all(self) -> list[BaseLLMProvider]:
        return list(self._providers.values())

    def list_by_capability(self, capability: str) -> list[BaseLLMProvider]:
        return [
            provider
            for provider in self._providers.values()
            if capability in provider.supported_capabilities()
        ]

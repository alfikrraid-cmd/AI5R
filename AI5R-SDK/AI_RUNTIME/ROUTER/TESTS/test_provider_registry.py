import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.exceptions import (
    ProviderAlreadyRegisteredError,
    ProviderNotRegisteredError,
)
from AI_RUNTIME.ROUTER.provider_registry import ProviderRegistry
from OSA.LLM_PROVIDER import LLMProviderRegistry, MockLLMProvider


def test_provider_registry_is_an_llm_provider_registry():
    assert issubclass(ProviderRegistry, LLMProviderRegistry)


def test_register_and_resolve():
    registry = ProviderRegistry()
    provider = MockLLMProvider()

    registry.register(provider)

    assert registry.resolve("MOCK") is provider


def test_resolve_unknown_provider_raises_typed_error():
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotRegisteredError):
        registry.resolve("UNKNOWN")


def test_register_replaces_by_default():
    registry = ProviderRegistry()
    first = MockLLMProvider()
    second = MockLLMProvider()

    registry.register(first)
    registry.register(second)

    assert registry.resolve("MOCK") is second


def test_register_disallow_replace_raises():
    registry = ProviderRegistry()
    registry.register(MockLLMProvider())

    with pytest.raises(ProviderAlreadyRegisteredError):
        registry.register(MockLLMProvider(), allow_replace=False)


def test_unregister_removes_provider():
    registry = ProviderRegistry()
    registry.register(MockLLMProvider())

    registry.unregister("MOCK")

    with pytest.raises(ProviderNotRegisteredError):
        registry.resolve("MOCK")


def test_unregister_unknown_provider_raises():
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotRegisteredError):
        registry.unregister("UNKNOWN")


def test_list_all_returns_every_registered_provider():
    registry = ProviderRegistry()
    provider = MockLLMProvider()
    registry.register(provider)

    assert registry.list_all() == [provider]


def test_list_by_capability_filters_by_supported_capabilities():
    registry = ProviderRegistry()
    provider = MockLLMProvider()
    registry.register(provider)

    assert registry.list_by_capability("chat") == [provider]
    assert registry.list_by_capability("vision") == []

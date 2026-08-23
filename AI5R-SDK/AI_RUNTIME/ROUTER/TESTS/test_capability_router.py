import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import pytest

from AI_RUNTIME.ROUTER.capability_router import CAPABILITIES, CapabilityRouter
from AI_RUNTIME.ROUTER.exceptions import CapabilityNotSupportedError
from AI_RUNTIME.ROUTER.provider_registry import ProviderRegistry
from OSA.LLM_PROVIDER import MockLLMProvider


def test_all_eleven_capabilities_defined():
    assert CAPABILITIES == {
        "coding",
        "architecture",
        "reasoning",
        "planning",
        "vision",
        "ocr",
        "translation",
        "embedding",
        "summarization",
        "tool_calling",
        "chat",
    }


def test_candidates_returns_providers_supporting_capability():
    registry = ProviderRegistry()
    provider = MockLLMProvider()
    registry.register(provider)
    router = CapabilityRouter(registry)

    assert router.candidates("chat") == [provider]


def test_candidates_raises_when_no_provider_supports_capability():
    registry = ProviderRegistry()
    registry.register(MockLLMProvider())
    router = CapabilityRouter(registry)

    with pytest.raises(CapabilityNotSupportedError):
        router.candidates("vision")

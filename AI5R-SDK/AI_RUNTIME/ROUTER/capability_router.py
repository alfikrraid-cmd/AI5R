from __future__ import annotations

from OSA.LLM_PROVIDER import BaseLLMProvider

from .exceptions import CapabilityNotSupportedError
from .provider_registry import ProviderRegistry

CAPABILITIES: frozenset[str] = frozenset(
    {
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
)


class CapabilityRouter:
    """First routing stage: Capability -> candidate providers.

    Reuses ``ProviderRegistry.list_by_capability`` unmodified — no second
    capability-matching mechanism is introduced.
    """

    def __init__(self, provider_registry: ProviderRegistry):
        self._provider_registry = provider_registry

    def candidates(self, capability: str) -> list[BaseLLMProvider]:
        matches = self._provider_registry.list_by_capability(capability)

        if not matches:
            raise CapabilityNotSupportedError(
                f"no registered provider supports capability '{capability}'"
            )

        return matches

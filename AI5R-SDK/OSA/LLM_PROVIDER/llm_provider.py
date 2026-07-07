from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LLMRequest:
    prompt: str
    system_prompt: str = ""
    temperature: float = 0.2
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class LLMResponse:
    provider: str
    model: str
    content: str
    finish_reason: str


class BaseLLMProvider(ABC):
    provider_name: str = "BASE"

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError


class MockLLMProvider(BaseLLMProvider):
    provider_name = "MOCK"

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.prompt:
            raise ValueError("prompt is required")

        return LLMResponse(
            provider=self.provider_name,
            model="mock-model",
            content=f"MOCK_RESPONSE::{request.prompt}",
            finish_reason="stop",
        )


class LLMProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}

    def register(self, provider: BaseLLMProvider):
        self._providers[provider.provider_name] = provider

    def resolve(self, provider_name: str) -> BaseLLMProvider:
        if provider_name not in self._providers:
            raise ValueError("provider is not registered")
        return self._providers[provider_name]

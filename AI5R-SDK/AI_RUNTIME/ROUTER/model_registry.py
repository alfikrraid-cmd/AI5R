from __future__ import annotations

from dataclasses import dataclass, field

from .exceptions import ModelNotRegisteredError


@dataclass(slots=True)
class ModelDescriptor:
    model_name: str
    provider_name: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    context_window: int = 0


class ModelRegistry:
    """Tracks which models exist, which provider serves them, and what each
    model supports/costs — orthogonal to ProviderRegistry (providers) and
    not duplicated by it."""

    def __init__(self) -> None:
        self._models: dict[str, ModelDescriptor] = {}

    def register(self, model: ModelDescriptor) -> None:
        self._models[model.model_name] = model

    def unregister(self, model_name: str) -> None:
        if model_name not in self._models:
            raise ModelNotRegisteredError(f"model '{model_name}' is not registered")
        del self._models[model_name]

    def get(self, model_name: str) -> ModelDescriptor:
        if model_name not in self._models:
            raise ModelNotRegisteredError(f"model '{model_name}' is not registered")
        return self._models[model_name]

    def list_all(self) -> list[ModelDescriptor]:
        return list(self._models.values())

    def list_by_provider(self, provider_name: str) -> list[ModelDescriptor]:
        return [m for m in self._models.values() if m.provider_name == provider_name]

    def list_by_capability(self, capability: str) -> list[ModelDescriptor]:
        return [m for m in self._models.values() if capability in m.capabilities]

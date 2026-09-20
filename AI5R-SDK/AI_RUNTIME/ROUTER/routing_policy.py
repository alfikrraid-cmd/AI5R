from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from OSA.LLM_PROVIDER import BaseLLMProvider

from .exceptions import RouterError


class RoutingPolicyError(RouterError):
    """Invalid AI5R_ROUTING_POLICY value."""


class RoutingMode(str, Enum):
    AUTO = "AUTO"
    DAHONO_PRIMARY = "DAHONO_PRIMARY"
    DIRECT_PRIMARY = "DIRECT_PRIMARY"
    LOCAL_FIRST = "LOCAL_FIRST"


class ProviderCategory(str, Enum):
    LOCAL = "LOCAL"
    DIRECT = "DIRECT"
    AGGREGATOR = "AGGREGATOR"


# Explicit classification keyed by each provider class's own `provider_name`.
# Deliberately NOT a default: a provider absent from this map is unclassified
# and never receives category priority (see RoutingPolicy.order).
PROVIDER_CATEGORIES: dict[str, ProviderCategory] = {
    "OLLAMA": ProviderCategory.LOCAL,
    "CLAUDE": ProviderCategory.DIRECT,
    "OPENAI": ProviderCategory.DIRECT,
    "GEMINI": ProviderCategory.DIRECT,
    "DEEPSEEK": ProviderCategory.DIRECT,
    "GROK": ProviderCategory.DIRECT,
    "OPENROUTER": ProviderCategory.AGGREGATOR,
    "LITELLM": ProviderCategory.AGGREGATOR,
    "DAHONO": ProviderCategory.AGGREGATOR,
}

DAHONO_PROVIDER_NAME = "DAHONO"


def category_of(provider: BaseLLMProvider) -> ProviderCategory | None:
    return PROVIDER_CATEGORIES.get(provider.provider_name)


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """Explicit ordering stage of ProviderSelector. Only reorders the candidates
    it is given (stable two-group sort: preferred group rank 0, the rest rank 1);
    it never adds, removes, or re-checks providers, so capability, health,
    budget and availability outcomes are unaffected."""

    mode: RoutingMode = RoutingMode.AUTO

    def _preferred(self, provider: BaseLLMProvider) -> bool:
        if self.mode is RoutingMode.DAHONO_PRIMARY:
            return provider.provider_name == DAHONO_PROVIDER_NAME
        if self.mode is RoutingMode.DIRECT_PRIMARY:
            return category_of(provider) is ProviderCategory.DIRECT
        if self.mode is RoutingMode.LOCAL_FIRST:
            return category_of(provider) is ProviderCategory.LOCAL
        return False

    def order(self, providers: list[BaseLLMProvider]) -> list[BaseLLMProvider]:
        if self.mode is RoutingMode.AUTO:
            return list(providers)
        return sorted(providers, key=lambda p: 0 if self._preferred(p) else 1)


def parse_routing_policy(value: str | None) -> RoutingPolicy:
    """Missing/blank -> AUTO. Any other value must be an exact mode name;
    anything else (including COST_OPTIMIZED) raises RoutingPolicyError."""

    if value is None or not value.strip():
        return RoutingPolicy(RoutingMode.AUTO)
    try:
        return RoutingPolicy(RoutingMode(value.strip()))
    except ValueError:
        valid = ", ".join(m.value for m in RoutingMode)
        raise RoutingPolicyError(
            f"invalid AI5R_ROUTING_POLICY {value.strip()!r}; valid values: {valid}"
        ) from None

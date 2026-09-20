from __future__ import annotations

import os

from OSA.LLM_PROVIDER import HealthStatus, LLMRequest, LLMResponse
from OSA.LLM_PROVIDER_OPENAI import OpenAICompatibleConfig, OpenAICompatibleProvider

DEFAULT_DAHONO_BASE_URL = "https://gateway.dahono.com/v1"
_CHAT_PATH = "/chat/completions"


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if base.endswith(_CHAT_PATH) else base + _CHAT_PATH


class DahonoProvider(OpenAICompatibleProvider):
    """Dahono AI Gateway -- text-only upstream provider (OpenAI-compatible
    chat/completions, Bearer auth). One candidate among the Router's providers;
    AI5R keeps provider-selection authority.

    There is intentionally NO default model: the model comes only from
    AI5R_DAHONO_MODEL. Until both key and model are set the provider reports
    unhealthy (excluded from routing) and refuses to generate.

    Known R1 limitation: Dahono's error contract is undocumented, so auth/policy
    failures are treated like any other provider failure by FallbackManager.
    """

    provider_name = "DAHONO"

    def __init__(self, config: OpenAICompatibleConfig | None = None):
        super().__init__(
            config
            or OpenAICompatibleConfig(
                api_key=os.getenv("AI5R_DAHONO_API_KEY", ""),
                model=os.getenv("AI5R_DAHONO_MODEL", ""),
                base_url=_chat_url(os.getenv("AI5R_DAHONO_BASE_URL", DEFAULT_DAHONO_BASE_URL)),
            )
        )

    @classmethod
    def from_env(cls) -> "DahonoProvider | None":
        """Fail closed: None unless both API key and model are configured."""
        if not os.getenv("AI5R_DAHONO_API_KEY") or not os.getenv("AI5R_DAHONO_MODEL"):
            return None
        return cls()

    def _configured(self) -> bool:
        return bool(self.config.api_key) and bool(self.config.model)

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.config.model:
            raise ValueError("model is required (set AI5R_DAHONO_MODEL)")
        return super().generate(request)

    def health(self) -> HealthStatus:
        if not self._configured():
            return HealthStatus(provider=self.provider_name, healthy=False, detail="not configured")
        return HealthStatus(provider=self.provider_name, healthy=True, detail="not monitored")

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"chat", "coding", "reasoning", "summarization", "translation"})

from __future__ import annotations

from OSA.LLM_PROVIDER_OPENAI import OpenAICompatibleConfig, OpenAICompatibleProvider


class GrokProvider(OpenAICompatibleProvider):
    """Grok (xAI) Provider — OpenAI-chat-completions-compatible API.

    Reuses ``OpenAICompatibleProvider.generate()`` unmodified; only default
    config and capability metadata differ.
    """

    provider_name = "GROK"

    def __init__(self, config: OpenAICompatibleConfig | None = None):
        import os

        super().__init__(
            config
            or OpenAICompatibleConfig(
                api_key=os.getenv("AI5R_GROK_API_KEY", ""),
                model=os.getenv("AI5R_GROK_MODEL", "grok-beta"),
                base_url=os.getenv("AI5R_GROK_BASE_URL", "https://api.x.ai/v1/chat/completions"),
            )
        )

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"chat", "reasoning", "coding"})

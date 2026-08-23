from __future__ import annotations

from OSA.LLM_PROVIDER_OPENAI import OpenAICompatibleConfig, OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter Provider — OpenAI-chat-completions-compatible aggregator API.

    Reuses ``OpenAICompatibleProvider.generate()`` unmodified; only default
    config and capability metadata differ.
    """

    provider_name = "OPENROUTER"

    def __init__(self, config: OpenAICompatibleConfig | None = None):
        import os

        super().__init__(
            config
            or OpenAICompatibleConfig(
                api_key=os.getenv("AI5R_OPENROUTER_API_KEY", ""),
                model=os.getenv("AI5R_OPENROUTER_MODEL", "openrouter/auto"),
                base_url=os.getenv(
                    "AI5R_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
                ),
            )
        )

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"chat", "coding", "reasoning", "summarization", "translation"})

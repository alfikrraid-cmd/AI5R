from __future__ import annotations

from OSA.LLM_PROVIDER_OPENAI import OpenAICompatibleConfig, OpenAICompatibleProvider


class LiteLLMProvider(OpenAICompatibleProvider):
    """LiteLLM Provider — talks to a LiteLLM proxy, which itself exposes an
    OpenAI-chat-completions-compatible endpoint in front of many backends.

    Reuses ``OpenAICompatibleProvider.generate()`` unmodified; only default
    config (a local proxy URL) and capability metadata differ.
    """

    provider_name = "LITELLM"

    def __init__(self, config: OpenAICompatibleConfig | None = None):
        import os

        super().__init__(
            config
            or OpenAICompatibleConfig(
                api_key=os.getenv("AI5R_LITELLM_API_KEY", ""),
                model=os.getenv("AI5R_LITELLM_MODEL", "gpt-4o-mini"),
                base_url=os.getenv(
                    "AI5R_LITELLM_BASE_URL", "http://localhost:4000/v1/chat/completions"
                ),
            )
        )

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"chat", "coding", "reasoning", "summarization", "tool_calling"})

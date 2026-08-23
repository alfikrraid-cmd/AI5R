from __future__ import annotations

from OSA.LLM_PROVIDER_OPENAI import OpenAICompatibleConfig, OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek Provider — OpenAI-chat-completions-compatible API.

    Reuses ``OpenAICompatibleProvider.generate()`` unmodified; only default
    config and capability metadata differ.
    """

    provider_name = "DEEPSEEK"

    def __init__(self, config: OpenAICompatibleConfig | None = None):
        import os

        super().__init__(
            config
            or OpenAICompatibleConfig(
                api_key=os.getenv("AI5R_DEEPSEEK_API_KEY", ""),
                model=os.getenv("AI5R_DEEPSEEK_MODEL", "deepseek-chat"),
                base_url=os.getenv(
                    "AI5R_DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions"
                ),
            )
        )

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"chat", "coding", "reasoning"})

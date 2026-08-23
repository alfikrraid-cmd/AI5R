from __future__ import annotations

from OSA.LLM_PROVIDER_OPENAI import OpenAICompatibleConfig, OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """The OpenAI Provider entry for AI_RUNTIME/ROUTER.

    Reuses ``OpenAICompatibleProvider.generate()`` unmodified (zero
    duplicated HTTP logic) — only default config and capability metadata
    differ from the base class.
    """

    provider_name = "OPENAI"

    def __init__(self, config: OpenAICompatibleConfig | None = None):
        import os

        super().__init__(
            config
            or OpenAICompatibleConfig(
                api_key=os.getenv("AI5R_OPENAI_API_KEY", ""),
                model=os.getenv("AI5R_OPENAI_MODEL", "gpt-4o-mini"),
                base_url=os.getenv(
                    "AI5R_OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"
                ),
            )
        )

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset(
            {"chat", "coding", "architecture", "reasoning", "planning", "summarization", "tool_calling"}
        )

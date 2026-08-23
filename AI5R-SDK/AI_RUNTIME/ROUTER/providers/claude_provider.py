from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from OSA.LLM_PROVIDER import BaseLLMProvider, LLMRequest, LLMResponse


@dataclass(slots=True)
class ClaudeConfig:
    api_key: str
    model: str = "claude-sonnet-5"
    base_url: str = "https://api.anthropic.com/v1/messages"
    max_tokens: int = 1024
    anthropic_version: str = "2023-06-01"


class ClaudeProvider(BaseLLMProvider):
    """Claude (Anthropic) Provider — Messages API, a distinct request/
    response shape and auth scheme (``x-api-key`` + ``anthropic-version``)
    from the OpenAI chat-completions family."""

    provider_name = "CLAUDE"

    def __init__(self, config: ClaudeConfig | None = None):
        self.config = config or ClaudeConfig(
            api_key=os.getenv("AI5R_CLAUDE_API_KEY", ""),
            model=os.getenv("AI5R_CLAUDE_MODEL", "claude-sonnet-5"),
            base_url=os.getenv("AI5R_CLAUDE_BASE_URL", "https://api.anthropic.com/v1/messages"),
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.prompt:
            raise ValueError("prompt is required")

        if not self.config.api_key:
            raise ValueError("api_key is required")

        payload: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt

        http_request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.config.api_key,
                "anthropic-version": self.config.anthropic_version,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(http_request, timeout=60) as response:
            raw = response.read().decode("utf-8")

        data: dict[str, Any] = json.loads(raw)
        content = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )

        return LLMResponse(
            provider=self.provider_name,
            model=data.get("model", self.config.model),
            content=content,
            finish_reason=data.get("stop_reason", "unknown"),
        )

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset(
            {
                "chat",
                "coding",
                "architecture",
                "reasoning",
                "planning",
                "vision",
                "tool_calling",
                "summarization",
            }
        )

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from OSA.LLM_PROVIDER import BaseLLMProvider, LLMRequest, LLMResponse


@dataclass(slots=True)
class OpenAICompatibleConfig:
    api_key: str
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1/chat/completions"


class OpenAICompatibleProvider(BaseLLMProvider):
    provider_name = "OPENAI_COMPATIBLE"

    def __init__(self, config: OpenAICompatibleConfig | None = None):
        self.config = config or OpenAICompatibleConfig(
            api_key=os.getenv("AI5R_LLM_API_KEY", ""),
            model=os.getenv("AI5R_LLM_MODEL", "gpt-4o-mini"),
            base_url=os.getenv(
                "AI5R_LLM_BASE_URL",
                "https://api.openai.com/v1/chat/completions",
            ),
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.prompt:
            raise ValueError("prompt is required")

        if not self.config.api_key:
            raise ValueError("api_key is required")

        payload = {
            "model": self.config.model,
            "temperature": request.temperature,
            "messages": self._messages(request),
        }

        http_request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(http_request, timeout=60) as response:
            raw = response.read().decode("utf-8")

        data: dict[str, Any] = json.loads(raw)
        choice = data["choices"][0]
        content = choice["message"]["content"]

        return LLMResponse(
            provider=self.provider_name,
            model=data.get("model", self.config.model),
            content=content,
            finish_reason=choice.get("finish_reason", "unknown"),
        )

    def _messages(self, request: LLMRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        if request.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": request.system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": request.prompt,
            }
        )

        return messages

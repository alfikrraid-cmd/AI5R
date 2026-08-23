from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from OSA.LLM_PROVIDER import BaseLLMProvider, LLMRequest, LLMResponse


@dataclass(slots=True)
class GeminiConfig:
    api_key: str
    model: str = "gemini-1.5-flash"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(BaseLLMProvider):
    """Gemini (Google) Provider — Generative Language API
    ``generateContent`` endpoint, a distinct request/response shape
    (API key as query parameter, ``contents``/``parts`` body) from the
    OpenAI chat-completions family."""

    provider_name = "GEMINI"

    def __init__(self, config: GeminiConfig | None = None):
        self.config = config or GeminiConfig(
            api_key=os.getenv("AI5R_GEMINI_API_KEY", ""),
            model=os.getenv("AI5R_GEMINI_MODEL", "gemini-1.5-flash"),
            base_url=os.getenv(
                "AI5R_GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/models",
            ),
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.prompt:
            raise ValueError("prompt is required")

        if not self.config.api_key:
            raise ValueError("api_key is required")

        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {"temperature": request.temperature},
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        url = f"{self.config.base_url}/{self.config.model}:generateContent?key={self.config.api_key}"

        http_request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(http_request, timeout=60) as response:
            raw = response.read().decode("utf-8")

        data: dict[str, Any] = json.loads(raw)
        candidate = data["candidates"][0]
        content = "".join(part.get("text", "") for part in candidate["content"]["parts"])

        return LLMResponse(
            provider=self.provider_name,
            model=self.config.model,
            content=content,
            finish_reason=candidate.get("finishReason", "unknown"),
        )

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"chat", "vision", "ocr", "reasoning", "translation", "summarization"})

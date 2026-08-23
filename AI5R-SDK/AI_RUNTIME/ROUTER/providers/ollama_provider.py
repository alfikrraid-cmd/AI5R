from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from OSA.LLM_PROVIDER import BaseLLMProvider, HealthStatus, LLMRequest, LLMResponse


@dataclass(slots=True)
class OllamaConfig:
    model: str = "llama3"
    base_url: str = "http://localhost:11434"


class OllamaProvider(BaseLLMProvider):
    """Ollama Provider — local REST API (``POST /api/generate``), a
    genuinely distinct shape from the OpenAI chat-completions family."""

    provider_name = "OLLAMA"

    def __init__(self, config: OllamaConfig | None = None):
        self.config = config or OllamaConfig(
            model=os.getenv("AI5R_OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("AI5R_OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.prompt:
            raise ValueError("prompt is required")

        prompt = request.prompt
        if request.system_prompt:
            prompt = f"{request.system_prompt}\n\n{request.prompt}"

        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": request.temperature},
        }

        http_request = urllib.request.Request(
            f"{self.config.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(http_request, timeout=60) as response:
            raw = response.read().decode("utf-8")

        data: dict[str, Any] = json.loads(raw)

        return LLMResponse(
            provider=self.provider_name,
            model=data.get("model", self.config.model),
            content=data.get("response", ""),
            finish_reason="stop" if data.get("done") else "unknown",
        )

    def health(self) -> HealthStatus:
        return HealthStatus(provider=self.provider_name, healthy=True, detail="local runtime")

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"chat", "coding", "reasoning"})

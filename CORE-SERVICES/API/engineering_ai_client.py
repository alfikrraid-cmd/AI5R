from __future__ import annotations

import json
from typing import Any

from AI_RUNTIME.ROUTER.model_registry import ModelDescriptor
from AI_RUNTIME.ROUTER.router import Router
from OSA.LLM_PROVIDER import CostEstimate, HealthStatus, LLMRequest

# MWO-AI-002: Engineering AI Client.
#
# Reuse before create: "AI_RUNTIME.ROUTER.Router" is documented in its own
# source (router.py) as "the single entry point every module SHALL call
# instead of talking to a provider directly." Repository archaeology
# (Reuse Report, this MWO's Implementation Report) confirmed Router already
# implements provider-agnostic routing, fallback, retry, cost-aware
# selection, and health aggregation across Claude/OpenAI/Gemini/DeepSeek/
# Ollama/LiteLLM providers -- all already built and tested under
# AI_RUNTIME/ROUTER/providers/. This class therefore contains NO routing,
# fallback, retry, or provider-selection logic of its own: every one of
# those concerns is delegated to the injected Router. This class is purely
# an LLM communication layer -- it accepts a prompt, returns a string or
# parsed JSON, and reports health/models/cost by reading what Router (and
# the providers it already wraps) already expose.
#
# No gateway access, no database access, no n8n call, no recommendation
# logic, no prompt construction, no business rules: this class never
# imports anything from CORE-SERVICES/API's gateway modules, and never
# modifies the prompt text it is given.


class EngineeringAIClient:
    """LLM communication layer only. Wraps an already-configured
    ``AI_RUNTIME.ROUTER.Router`` (dependency injection -- this class never
    constructs a Router or registers providers itself, since provider
    construction/configuration is already each provider's own existing
    responsibility, read from environment variables per provider, e.g.
    ``AI5R_CLAUDE_API_KEY``, ``AI5R_GEMINI_API_KEY``, ``AI5R_LLM_API_KEY``
    for OpenAI-compatible providers including LiteLLM/DeepSeek). This
    class introduces no new configuration surface and hardcodes nothing.
    """

    def __init__(self, router: Router, default_provider: str | None = None):
        self._router = router
        self._default_provider = default_provider

    # -- responsibilities -------------------------------------------------

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.2,
        capability: str = "chat",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        request = LLMRequest(
            prompt=prompt, system_prompt=system_prompt, temperature=temperature, metadata=metadata
        )
        response = self._dispatch(request, capability)
        return response.content

    def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.2,
        capability: str = "chat",
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        # The prompt is used exactly as given -- this method does not
        # construct or modify prompt text (prompt construction belongs to
        # EngineeringPromptBuilder). json.loads() here deserializes the
        # LLM response's own wire format, the same transport-level
        # responsibility every provider's generate() already performs on
        # its raw HTTP body (see e.g. OpenAICompatibleProvider.generate());
        # it is not business-data parsing.
        content = self.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            capability=capability,
            metadata=metadata,
        )
        return json.loads(content)

    def health(self) -> dict[str, HealthStatus]:
        return self._router.health()

    def list_models(self) -> list[ModelDescriptor]:
        # ModelRegistry already exists on Router (model_registry.py) but is
        # unwired by any Router method today -- reused here unchanged
        # rather than introducing a second model catalog.
        return self._router.model_registry.list_all()

    def estimate_cost(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float = 0.2,
        capability: str = "chat",
    ) -> CostEstimate:
        request = LLMRequest(prompt=prompt, system_prompt=system_prompt, temperature=temperature)
        provider = self._resolve_provider(capability, request)
        # Delegates to the provider's own estimate_cost() (BaseLLMProvider
        # contract) -- no cost computation is duplicated here, matching
        # how AI_RUNTIME.ROUTER.CostPolicy itself delegates to providers.
        return provider.estimate_cost(request)

    def switch_model(self, provider_name: str | None) -> None:
        """Optional: pin subsequent generate()/generate_json() calls to one
        specific, already-registered provider, bypassing Router's normal
        fallback/ranking pipeline. Pass None to clear the pin and restore
        full Router-managed selection."""

        if provider_name is not None:
            self._router.provider_registry.resolve(provider_name)  # raises if not registered
        self._default_provider = provider_name

    # -- internal dispatch --------------------------------------------------

    def _dispatch(self, request: LLMRequest, capability: str):
        if self._default_provider is not None:
            provider = self._router.provider_registry.resolve(self._default_provider)
            return provider.generate(request)
        return self._router.generate(request, capability=capability)

    def _resolve_provider(self, capability: str, request: LLMRequest):
        if self._default_provider is not None:
            return self._router.provider_registry.resolve(self._default_provider)
        # Reuses Router's own existing candidate-selection collaborators
        # (CapabilityRouter, ProviderSelector) rather than reimplementing
        # provider ranking for cost estimation.
        candidates = self._router.capability_router.candidates(capability)
        ordered = self._router.provider_selector.order(candidates, request)
        return ordered[0]

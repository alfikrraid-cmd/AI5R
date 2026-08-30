"""MWO-AI5R-LTSA-AI-ORCHESTRATION-001 -- minimum orchestration layer over
the existing deterministic Copilot tools (copilot_ask_service.TOOL_HANDLERS)
and the existing, already-tested LLM runtime (AI5R-SDK/AI_RUNTIME/ROUTER,
reused unmodified via CORE-SERVICES/API/engineering_ai_client.py's own
EngineeringAIClient, MWO-AI-002). No new AI platform, no vector DB, no
LTSA_BRAIN activation, no hardcoded credential -- see
CORE-SERVICES/BACKEND-API/dependencies.py's get_copilot_ai_client() for how
(and only-if-configured-via-env) a Router/EngineeringAIClient is built.

Exactly two bounded LLM calls, no loop, no recursion, no autonomous
behavior:
  1. TOOL SELECTION -- given the question + asset tag + a fixed catalog of
     tool NAME -> one-line description (never the tools' implementation or
     any data), the LLM returns which existing tools to run (capped at
     MAX_TOOLS_PER_REQUEST). An unrecognized name is silently dropped, never
     executed -- the LLM can pick from this whitelist only; it cannot name
     a query, a table, or arbitrary code, so there is no path from an LLM
     response to SQL or any other execution surface.
  2. SYNTHESIS -- given ONLY the already-executed tools' own structured,
     evidence-bearing CopilotAnswer output (never a raw DB/history dump),
     the LLM produces a grounded explanation plus a FACT/INTERPRETATION/
     RECOMMENDATION/DATA_GAP classification.

The LLM is NEVER the source of a fact: every item in the returned
evidence[] comes from a TOOL_HANDLERS call, gated by the SAME server-side
area/MA scope guard routers/copilot.py already applies before
orchestrate_copilot() is ever invoked (unchanged from the deterministic
path) -- this module receives an already scope-checked `tag`, never
re-derives or trusts one from the question text or from the LLM.
"Missing evidence -> DATA_GAP" (Hard Rule) is enforced HERE,
deterministically, after the LLM call returns -- never left to the model's
own say-so alone: if every executed tool's evidence tuple is empty, kind
is forced to DATA_GAP regardless of what the synthesis step returned.

FALLBACK: any AI failure at all (no client configured, network error,
timeout, malformed JSON, unrecognized tool selection, anything) falls back
to the existing single-intent deterministic dispatcher
(copilot_ask_service.ask_copilot) unchanged -- a provider outage must
never break Copilot, and must never be presented as a fabricated answer.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from .copilot_ask_service import (
    DATA_GAP,
    FACT,
    INTERPRETATION,
    RECOMMENDATION,
    CopilotAnswer,
    TOOL_HANDLERS,
    ask_copilot,
)

MAX_TOOLS_PER_REQUEST = 5

# name -> one-line description ONLY -- the LLM never sees implementation,
# gateway objects, or data here, just this whitelist of selectable names.
TOOL_CATALOG: dict[str, str] = {
    "pump_status": "Current run/standby status, area, and location of the pump.",
    "pump_history": "Maintenance history records for the pump.",
    "work_orders": "Active work orders for the pump.",
    "pm": "Most recent Preventive Maintenance (PM) activity.",
    "cm": "Most recent Corrective Maintenance (CM) report.",
    "current_seal": "The pump's single currently-installed mechanical seal, from installation evidence only.",
    "seal_compat": "Mechanical seals registered as compatible with this pump (a broader list, not the current seal).",
    "inventory": "Spare-part stock on hand for this pump's compatible seals.",
    "drawing_document": "Engineering drawings/documents for this pump's compatible seals.",
    "installation": "Installation report history for this pump.",
    "recommendation": "Deterministic, rule-based engineering recommendations for this pump.",
    "condition_monitoring": "Latest Condition Monitoring reading/finding for this pump.",
}

_VALID_KINDS = (FACT, INTERPRETATION, RECOMMENDATION, DATA_GAP)

_SELECTION_SYSTEM_PROMPT = (
    "You select which read-only engineering tools to call to answer a "
    "pump/mechanical-seal maintenance question. Choose only from the given "
    "tool list -- never invent a tool name. A/B/C-suffixed asset tags are "
    "distinct physical assets; never assume one tag's data answers a "
    "question about a different tag. Respond with strict JSON only, no "
    "prose, no explanation."
)
_SYNTHESIS_SYSTEM_PROMPT = (
    "You are an LTSA engineering assistant. Use ONLY the given tool "
    "results as facts -- never invent dates, seal codes, stock levels, "
    "failures, PM/CM records, drawings, or recommendations. Present a "
    "recommendation as a recommendation, never as a confirmed fact. If "
    "evidence for part of the question is missing or the tool results "
    "conflict, say so explicitly and prefer kind DATA_GAP. Respond with "
    "strict JSON only, no prose, no chain-of-thought."
)


class AIClient(Protocol):
    def generate_json(
        self, prompt: str, *, system_prompt: str = "", temperature: float = 0.2
    ) -> Any: ...


def orchestrate_copilot(
    question: str,
    tag: str | None,
    scope: frozenset[str] | None,
    ai_client: AIClient | None,
    **service_deps: Any,
) -> tuple[CopilotAnswer, list[str]]:
    """Returns (answer, tools_used). tools_used is [] whenever the
    deterministic dispatcher answered instead of the AI path (no client
    configured, tag-less question, or any AI failure)."""

    if ai_client is None or tag is None:
        # No AI client configured (dependencies.get_copilot_ai_client()
        # found no provider env vars -- see that function's own docstring),
        # or a global/tag-less question -- the existing deterministic
        # dispatcher already handles both correctly, including the
        # scope-filtered global work-orders intent.
        return ask_copilot(question, tag, scope, **service_deps), []

    try:
        tool_names = _select_tools(ai_client, question, tag)
        if not tool_names:
            return ask_copilot(question, tag, scope, **service_deps), []

        results: dict[str, CopilotAnswer] = {}
        for name in tool_names[:MAX_TOOLS_PER_REQUEST]:
            handler = TOOL_HANDLERS.get(name)
            if handler is None:
                continue  # not in the whitelist -- silently dropped, never executed
            results[name] = handler(tag, **service_deps)

        if not results:
            return ask_copilot(question, tag, scope, **service_deps), []

        answer = _synthesize(ai_client, question, tag, results)
        return answer, list(results.keys())
    except Exception:
        # Any AI-path failure (unreachable provider, timeout, malformed
        # JSON, anything) -- never break Copilot, never fabricate.
        return ask_copilot(question, tag, scope, **service_deps), []


def _select_tools(ai_client: AIClient, question: str, tag: str) -> list[str]:
    catalog_text = "\n".join(f"- {name}: {desc}" for name, desc in TOOL_CATALOG.items())
    prompt = (
        f"Question about asset {tag}: {question!r}\n\n"
        f"Available tools:\n{catalog_text}\n\n"
        f'Return ONLY JSON: {{"tools": [<up to {MAX_TOOLS_PER_REQUEST} tool '
        f"names from the list above, most relevant first>]}}."
    )
    result = ai_client.generate_json(prompt, system_prompt=_SELECTION_SYSTEM_PROMPT, temperature=0.0)
    tools = result.get("tools") if isinstance(result, dict) else None
    if not isinstance(tools, list):
        return []
    return [name for name in tools if isinstance(name, str) and name in TOOL_CATALOG]


def _synthesize(ai_client: AIClient, question: str, tag: str, results: dict[str, CopilotAnswer]) -> CopilotAnswer:
    # Only the tools' own already-computed, evidence-bearing output is
    # sent -- never a raw DB dump, never unrelated history (token/cost
    # control, and the actual factual boundary the LLM may reason within).
    tool_results_json = json.dumps(
        {name: {"answer": r.answer, "kind": r.kind, "evidence": list(r.evidence)} for name, r in results.items()}
    )
    prompt = (
        f"Question about asset {tag}: {question!r}\n\n"
        f"Tool results (the ONLY facts you may use):\n{tool_results_json}\n\n"
        'Return ONLY JSON: {"answer": <grounded explanation citing the tool '
        'facts above; state DATA_GAP explicitly for anything missing or '
        'conflicting>, "kind": "FACT"|"INTERPRETATION"|"RECOMMENDATION"|"DATA_GAP"}.'
    )
    result = ai_client.generate_json(prompt, system_prompt=_SYNTHESIS_SYSTEM_PROMPT, temperature=0.2)
    answer_text = result.get("answer") if isinstance(result, dict) else None
    kind = result.get("kind") if isinstance(result, dict) else None
    if not isinstance(answer_text, str) or not answer_text.strip():
        raise ValueError("AI synthesis returned no usable answer")
    if kind not in _VALID_KINDS:
        kind = INTERPRETATION

    evidence = tuple(item for r in results.values() for item in r.evidence)
    if not evidence:
        # Hard rule enforced here, not trusted to the model alone: no
        # evidence from any executed tool means no fact was actually
        # confirmed, regardless of what the LLM's own `kind` claimed.
        kind = DATA_GAP

    return CopilotAnswer(answer_text, kind, evidence)


__all__ = ["orchestrate_copilot", "TOOL_CATALOG", "MAX_TOOLS_PER_REQUEST", "AIClient"]

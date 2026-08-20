"""
MWO-LTSA-035 -- EngineeringInsight: deterministic, rule-free derivation of
Root Cause / Risk / Recommended Action / Confidence from already-computed
RecommendationEngine and EngineeringContextEngine output. No LLM, no
OpenAI, no Claude, no Ollama, no network, no prompt -- pure field
selection over data those two components already produced. No new
business rules: the actual classification/urgency rules remain entirely
owned by RecommendationEngine (priority, confidence) and
EngineeringContextEngine (cm_summary.overall_condition).

Root Cause / Recommended Action / Confidence: taken from the
highest-priority Recommendation (index 0). RecommendationEngine.recommend()
already returns recommendations sorted by priority descending -- this
module does not re-derive or re-rank that order, it only reads index 0.

Risk: taken verbatim from EngineeringContextEngine's own
summary["cm_summary"]["overall_condition"] (NORMAL/ABNORMAL/CRITICAL) --
the same signal already reused elsewhere in this pipeline
(useKnowledgeWorkspace.js's equipment.risk mapping), not re-classified.

If no Recommendation exists, there is nothing to build an insight from --
returns None rather than fabricating placeholder content, matching this
codebase's established "disclosed gap, not invented" discipline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .recommendation_engine import Recommendation


@dataclass(frozen=True, slots=True)
class EngineeringInsight:
    """Immutable: deterministic engineering insight for one pump."""

    root_cause: str
    risk: str | None
    recommended_action: str
    confidence: float


def build_engineering_insight(
    recommendations: "tuple[Recommendation, ...]",
    summary: dict[str, Any] | None = None,
) -> EngineeringInsight | None:
    if not recommendations:
        return None

    top = recommendations[0]
    risk = (summary or {}).get("cm_summary", {}).get("overall_condition")

    return EngineeringInsight(
        root_cause=top.description,
        risk=risk,
        recommended_action=top.action,
        confidence=top.confidence,
    )


__all__ = ["EngineeringInsight", "build_engineering_insight"]

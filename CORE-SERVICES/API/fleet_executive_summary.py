"""
MWO-LTSA-037E -- FleetExecutiveSummaryService: deterministic executive
rollup over the fleet, built entirely from three already-existing, reused
building blocks -- FleetReliabilityService (fleet-wide totals,
MWO-LTSA-037B), ExecutiveMetrics (indirectly: FleetReliability's own
fields are already computed from it, never recomputed here), and
RecommendationEngine (indirectly: knowledge.recommendation is already
populated by LTSAKnowledgeService.build(), never invoked a second time
here). No LLM, no prompt, no new gateway, no new pump-discovery logic.

Per-pump detail (needed for Critical Assets / Top Risks -- both inherently
per-pump, unlike FleetReliability's pure totals) comes from
FleetReliabilityService.list_pump_knowledge() (this MWO's own minimal,
additive extension to that service) -- not from a second, independent
PumpGateway/LTSAKnowledgeService call site.

Field derivation:
  - overall_health / fleet_availability / fleet_mtbf_days /
    fleet_mttr_hours / breakdown_count / critical_spare_count: pass
    through FleetReliability's own fleet_health_score / fleet_availability
    / fleet_mtbf_days / fleet_mttr_hours / total_breakdown_count /
    total_critical_spare_count unchanged -- no re-derivation. (MTBF/MTTR
    added under MWO-LTSA-038B, which needs to display them; still exactly
    one FleetReliabilityService.build() call -- no new calculation, no
    second service call.)
  - fleet_status: a new, disclosed 4-band classification of overall_health
    (NORMAL >= 80, ATTENTION >= 50, CRITICAL below, UNKNOWN when no health
    score exists) -- no existing status-banding logic exists anywhere in
    the repository for a continuous 0-100 health score to reuse (confirmed
    by repository archaeology); the NORMAL/ATTENTION/CRITICAL vocabulary
    itself is reused from the existing cm_summary.overall_condition ->
    risk mapping already established elsewhere (useKnowledgeWorkspace.js's
    CM_CONDITION_TO_RISK), not invented fresh.
  - critical_asset_count: number of pumps carrying at least one
    Recommendation with priority >= RecommendationEngine's own
    PRIORITY_CRITICAL constant (100) -- reuses that existing threshold,
    not a newly invented one.
  - top_risks: every pump's Recommendations flattened, sorted by priority
    descending (ties keep pump-then-rule evaluation order, the same
    stable-sort determinism RecommendationEngine.recommend() itself
    already relies on), capped at TOP_RISKS_LIMIT. Not a "bad actor"
    per-pump ranking (no pump-level scoring/sorting is introduced) -- it
    is a flat list of the fleet's own already-computed Recommendation
    objects, ranked by the same priority field RecommendationEngine
    already assigns.

Explicitly out of scope, per this MWO: no LLM, no prompt, no backend
duplication of any value FleetReliabilityService/ExecutiveMetrics/
RecommendationEngine already computed.
"""

from __future__ import annotations

from dataclasses import dataclass

from .fleet_reliability_service import FleetReliabilityService
from .recommendation_engine import PRIORITY_CRITICAL

TOP_RISKS_LIMIT = 5

HEALTH_NORMAL_THRESHOLD = 80
HEALTH_ATTENTION_THRESHOLD = 50


@dataclass(frozen=True, slots=True)
class TopRisk:
    """Immutable: one fleet-wide risk entry, carrying the Recommendation
    fields an executive summary needs, plus which pump it came from.

    MWO-LTSA-037F -- description added (reused unchanged from
    Recommendation.description) so FleetInsight can derive its Reason
    field without reaching back past FleetExecutiveSummary into raw
    per-pump knowledge a second time."""

    tag_number: str
    rule_code: str
    title: str
    priority: int
    action: str
    description: str


@dataclass(frozen=True, slots=True)
class FleetExecutiveSummary:
    """Immutable: one deterministic executive-level rollup of the fleet.
    Fields with no supporting data are None, never fabricated."""

    overall_health: float | None
    fleet_status: str
    critical_asset_count: int
    fleet_availability: float | None
    fleet_mtbf_days: float | None
    fleet_mttr_hours: float | None
    breakdown_count: int
    critical_spare_count: int
    top_risks: tuple[TopRisk, ...]


class FleetExecutiveSummaryService:
    """Builds one FleetExecutiveSummary by composing
    FleetReliabilityService's fleet-wide totals with a per-pump scan of
    already-computed Recommendations. No new gateway, no SQL, no API, no
    UI, no LLM."""

    def __init__(self, fleet_reliability_service: FleetReliabilityService | None = None) -> None:
        self.fleet_reliability_service = fleet_reliability_service or FleetReliabilityService()

    def build(self) -> FleetExecutiveSummary:
        reliability = self.fleet_reliability_service.build()
        knowledge = self.fleet_reliability_service.list_pump_knowledge()

        return FleetExecutiveSummary(
            overall_health=reliability.fleet_health_score,
            fleet_status=_fleet_status(reliability.fleet_health_score),
            critical_asset_count=_count_critical_assets(knowledge),
            fleet_availability=reliability.fleet_availability,
            fleet_mtbf_days=reliability.fleet_mtbf_days,
            fleet_mttr_hours=reliability.fleet_mttr_hours,
            breakdown_count=reliability.total_breakdown_count,
            critical_spare_count=reliability.total_critical_spare_count,
            top_risks=_top_risks(knowledge),
        )


def _fleet_status(fleet_health_score: float | None) -> str:
    if fleet_health_score is None:
        return "UNKNOWN"
    if fleet_health_score >= HEALTH_NORMAL_THRESHOLD:
        return "NORMAL"
    if fleet_health_score >= HEALTH_ATTENTION_THRESHOLD:
        return "ATTENTION"
    return "CRITICAL"


def _count_critical_assets(knowledge) -> int:
    return sum(1 for pump in knowledge if _is_critical_asset(pump))


def _is_critical_asset(pump) -> bool:
    return any(rec.priority >= PRIORITY_CRITICAL for rec in (pump.recommendation or ()))


def _top_risks(knowledge) -> tuple[TopRisk, ...]:
    risks = [
        TopRisk(
            tag_number=pump.tag_number,
            rule_code=rec.rule_code,
            title=rec.title,
            priority=rec.priority,
            action=rec.action,
            description=rec.description,
        )
        for pump in knowledge
        for rec in (pump.recommendation or ())
    ]
    ranked = sorted(risks, key=lambda risk: risk.priority, reverse=True)
    return tuple(ranked[:TOP_RISKS_LIMIT])


__all__ = ["FleetExecutiveSummary", "FleetExecutiveSummaryService", "TopRisk"]

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

from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from . import maintenance_intelligence_service as mis
from .engineering_context_engine import EngineeringContextEngine
from .fleet_reliability_service import FleetReliabilityService
from .ltsa_knowledge_service import LTSAKnowledge
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
    # MWO-LTSA-FLEET-ATTENTION-001 -- additive fields, top_risks itself
    # unchanged (may still carry more than one entry for the same pump --
    # existing consumers of top_risks keep their exact current behavior).
    # top_risk_pumps is the SAME ranking deduplicated to at most one entry
    # per pump (its own single highest-priority recommendation), capped at
    # TOP_RISKS_LIMIT pumps -- what a "which pumps need attention" WhatsApp
    # answer actually needs (one row per pump, never two rows for the same
    # pump crowding out a different one). attention_pump_count is the total
    # number of DISTINCT pumps carrying at least one recommendation, so a
    # renderer can say "N more pumps" truthfully instead of guessing.
    top_risk_pumps: tuple[TopRisk, ...] = ()
    attention_pump_count: int = 0


class FleetExecutiveSummaryService:
    """Builds one FleetExecutiveSummary by composing
    FleetReliabilityService's fleet-wide totals with a per-pump scan of
    already-computed Recommendations. No new gateway, no SQL, no API, no
    UI, no LLM."""

    def __init__(self, fleet_reliability_service: FleetReliabilityService | None = None) -> None:
        self.fleet_reliability_service = fleet_reliability_service or FleetReliabilityService()

    def build(self, *, scope: frozenset[str] | None = None) -> FleetExecutiveSummary:
        # MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 -- scope threads
        # through to FleetReliabilityService's own pump-discovery choke
        # point (see that service's own build()/list_pump_knowledge()
        # comment) -- every field below (including top_risks, the actual
        # per-pump leak vector this closure exists to fix) is therefore
        # already computed from only in-scope pumps, never filtered
        # after the fact.
        #
        # MWO-LTSA-FLEET-ATTENTION-001 -- list_pump_knowledge() is now
        # called exactly ONCE (previously: once here, and a second,
        # entirely redundant time inside fleet_reliability_service.build()
        # -- the single dominant cause of this query's own reported
        # latency, doubling every per-pump gateway round trip in the
        # fleet). aggregate_from_knowledge() is a pure, no-I/O function
        # over the SAME already-fetched knowledge -- no second fetch.
        #
        # MWO-LTSA-FLEET-ANALYTICS-001 -- list_pump_knowledge_fast() uses
        # the O(1)-total-gateway-call batch path when the production
        # singleton FleetReliabilityService was constructed with the
        # batch-sourcing dependencies (dependencies.py), replacing what
        # was still, until now, a one-gateway-round-trip-per-pump fetch
        # for seal compatibility/seals/stock/PM/CM/CMON/PM-schedule. Falls
        # back to the original per-pump list_pump_knowledge() when those
        # dependencies are absent (e.g. a test building this service with
        # only pump_gateway/ltsa_knowledge_service) -- identical output,
        # only the fetch strategy differs.
        knowledge = self.fleet_reliability_service.list_pump_knowledge_fast(scope=scope)
        reliability = self.fleet_reliability_service.aggregate_from_knowledge(knowledge)

        # MWO-LTSA-FLEET-ATTENTION-001 -- fleet ranking must reflect
        # CURRENT/unresolved evidence (active leak, PM overdue/due-soon),
        # not just the no-summary recommendation set LTSAKnowledgeService.
        # build() bakes into knowledge.recommendation (see this module's
        # own header comment / RecommendationEngine.recommend()'s own
        # docstring: summary is optional and every pre-020B caller,
        # LTSAKnowledgeService.build() included, keeps getting the
        # pre-020B set). Recomputed here, per pump, from data ALREADY
        # fetched (condition_monitoring_readings, pm_schedules) -- zero
        # additional gateway/DB calls -- so REC_ACTIVE_LEAK (95) and
        # REC_PM_OVERDUE (80) are considered for fleet ranking exactly as
        # they already are for a single-pump /copilot/ask "recommendation"
        # question via routers/engineering_ai.py, never a second,
        # divergent rule set.
        fleet_aware_knowledge = tuple(
            self._with_fleet_aware_recommendation(pump) for pump in knowledge
        )

        return FleetExecutiveSummary(
            overall_health=reliability.fleet_health_score,
            fleet_status=_fleet_status(reliability.fleet_health_score),
            critical_asset_count=_count_critical_assets(fleet_aware_knowledge),
            fleet_availability=reliability.fleet_availability,
            fleet_mtbf_days=reliability.fleet_mtbf_days,
            fleet_mttr_hours=reliability.fleet_mttr_hours,
            breakdown_count=reliability.total_breakdown_count,
            critical_spare_count=reliability.total_critical_spare_count,
            top_risks=_top_risks(fleet_aware_knowledge),
            top_risk_pumps=_top_risk_pumps(fleet_aware_knowledge),
            attention_pump_count=_attention_pump_count(fleet_aware_knowledge),
        )

    def _with_fleet_aware_recommendation(self, knowledge: LTSAKnowledge) -> LTSAKnowledge:
        summary = _build_minimal_summary(knowledge)
        recommendation_engine = self.fleet_reliability_service.ltsa_knowledge_service.recommendation_engine
        return replace(knowledge, recommendation=recommendation_engine.recommend(knowledge, summary))


def _build_minimal_summary(knowledge: LTSAKnowledge) -> dict[str, Any]:
    """MWO-LTSA-FLEET-ATTENTION-001 -- the minimal subset of
    EngineeringContextEngine.build()'s own summary shape that RecommendationEngine's
    active-leak and PM-due rules actually read, computed PURELY from
    knowledge's own already-fetched fields (condition_monitoring_readings,
    pm_schedules) -- no gateway call, no second fetch of anything.

    cm_summary.leak_flag reuses maintenance_intelligence_service's own
    canonical windowing rule (leak_flag_from_readings, extracted from
    get_pump_condition_monitoring_flag -- the exact function
    EngineeringContextEngine._build_cm_summary itself calls), not a
    reinvented one. pm_summary.status reuses EngineeringContextEngine's own
    static _compute_pm_status, not a reinvented OVERDUE/DUE_SOON rule."""
    leak = mis.leak_flag_from_readings(knowledge.condition_monitoring_readings)
    latest_abnormal_values = None
    if leak["flagged"] and leak["latest_flagged_reading"]:
        reading = leak["latest_flagged_reading"]
        latest_abnormal_values = {
            "reading_code": reading.get("condition_monitoring_reading_code"),
            "reading_date": reading.get("reading_date"),
            "mechanical_seal_leak_de": reading.get("mechanical_seal_leak_de"),
            "mechanical_seal_leak_nde": reading.get("mechanical_seal_leak_nde"),
        }
    cm_summary = {"leak_flag": leak["flagged"], "latest_abnormal_values": latest_abnormal_values}

    schedules_sorted = sorted(knowledge.pm_schedules or [], key=lambda record: record.get("next_due") or "")
    schedule = schedules_sorted[0] if schedules_sorted else None
    today = date.today()
    status = EngineeringContextEngine._compute_pm_status(schedule, today)
    pm_summary = {"status": status}

    evidence: list[dict[str, Any]] = []
    if status == "OVERDUE" and schedule is not None:
        evidence.append(
            {"flag": "PM_OVERDUE", "source": "PMSchedule", "reference": schedule.get("pm_schedule_code")}
        )

    return {"cm_summary": cm_summary, "pm_summary": pm_summary, "evidence": evidence}


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


def _pump_top_recommendation(pump) -> Any | None:
    recommendations = pump.recommendation or ()
    if not recommendations:
        return None
    # RecommendationEngine.recommend() already returns its own output
    # sorted by priority descending (stable sort, ties keep rule-evaluation
    # order) -- recommendations[0] is already that pump's own single
    # highest-priority recommendation, no re-sorting needed.
    return recommendations[0]


def _top_risk_pumps(knowledge) -> tuple[TopRisk, ...]:
    per_pump = [
        (pump.tag_number, rec)
        for pump in knowledge
        for rec in (_pump_top_recommendation(pump),)
        if rec is not None
    ]
    ranked = sorted(per_pump, key=lambda item: item[1].priority, reverse=True)
    return tuple(
        TopRisk(
            tag_number=tag_number,
            rule_code=rec.rule_code,
            title=rec.title,
            priority=rec.priority,
            action=rec.action,
            description=rec.description,
        )
        for tag_number, rec in ranked[:TOP_RISKS_LIMIT]
    )


def _attention_pump_count(knowledge) -> int:
    return sum(1 for pump in knowledge if pump.recommendation)


__all__ = ["FleetExecutiveSummary", "FleetExecutiveSummaryService", "TopRisk"]

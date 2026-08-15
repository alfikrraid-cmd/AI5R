"""
MWO-LTSA-036N -- Executive Metrics: deterministic Executive Dashboard KPI
building blocks over an already-built LTSAKnowledge aggregate, in the same
composition style as RecommendationEngine (031F/R1) and EngineeringInsight
(035): a pure function of fields LTSAKnowledgeService already assembles.
No new aggregate, no new gateway, no SQL, no second Knowledge API call --
the caller is expected to already hold an LTSAKnowledge built by the
existing LTSAKnowledgeService.build().

Scope note ("foundation"): computes the six required metrics for ONE
pump's LTSAKnowledge. A fleet-wide Executive Dashboard would call this
once per pump (reusing PumpGateway.list_pumps() +
LTSAKnowledgeService.build(), both already real) and aggregate the
per-pump results across the fleet -- that aggregation and any new router/
endpoint is explicitly out of this MWO's scope (no router change was
requested) and is left for a follow-up MWO.

Data sources considered and the source actually used, per metric:
  - health_score: reuses RecommendationEngine's own priority scale
    (100/90/70, already computed on knowledge.recommendation) as the
    deduction -- no new severity scale invented.
  - mtbf_days / mttr_hours: both read from cm_history (cm_report), this
    product's own canonical "reactive failure record"
    (CANONICAL_SCHEMA.sql's own comment) -- not breakdown_history (a
    maintenance_history/work_order-linked view of the same underlying
    activity, a different granularity, kept separate since this MWO
    tracks "Breakdown" as its own, distinct metric). mttr_hours reads
    cm_report.downtime_hours, a real stored column -- never derived from
    a start/end pair that does not exist in the schema.
  - pm_compliance_rate: reimplements the exact same "not overdue"
    definition utils/executiveDashboard.js's buildMaintenanceHealth
    already established client-side -- independently expressed here
    since no shared calculation service exists between the two stacks,
    not a new business rule. 0 when there are no PM Schedules at all,
    matching that same existing convention's own default.
  - breakdown_count: len(breakdown_history), already the exact list
    LTSAKnowledgeService assembles for this concept -- no new filter.
  - critical_spare_count: reuses the same "missing stock" definition
    RecommendationEngine._check_zero_inventory's own _is_missing_stock
    rule already established (quantity_on_hand is None or <= 0),
    independently expressed here (not imported) since that helper is
    module-private to recommendation_engine.py -- same business rule,
    not a new one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .ltsa_knowledge_service import LTSAKnowledge


@dataclass(frozen=True, slots=True)
class ExecutiveMetrics:
    """Immutable: one pump's Executive Dashboard KPI set, derived entirely
    from an already-built LTSAKnowledge. Fields with no supporting data
    are None, never fabricated as a placeholder number."""

    tag_number: str
    health_score: int
    mtbf_days: float | None
    mttr_hours: float | None
    pm_compliance_rate: int
    breakdown_count: int
    critical_spare_count: int


def compute_executive_metrics(knowledge: "LTSAKnowledge", today: date | None = None) -> ExecutiveMetrics:
    today = today or date.today()

    return ExecutiveMetrics(
        tag_number=knowledge.tag_number,
        health_score=_compute_health_score(knowledge),
        mtbf_days=_compute_mtbf_days(knowledge),
        mttr_hours=_compute_mttr_hours(knowledge),
        pm_compliance_rate=_compute_pm_compliance_rate(knowledge, today),
        breakdown_count=len(knowledge.breakdown_history),
        critical_spare_count=_compute_critical_spare_count(knowledge),
    )


def _compute_health_score(knowledge: "LTSAKnowledge") -> int:
    recommendations = knowledge.recommendation or ()
    worst_priority = max((rec.priority for rec in recommendations), default=0)
    return max(0, 100 - worst_priority)


def _compute_mtbf_days(knowledge: "LTSAKnowledge") -> float | None:
    timestamps = sorted(
        parsed
        for record in knowledge.cm_history
        if (parsed := _parse_date(record.get("created_at"))) is not None
    )
    if len(timestamps) < 2:
        return None

    gaps = [(timestamps[i + 1] - timestamps[i]).days for i in range(len(timestamps) - 1)]
    return mean(gaps)


def _compute_mttr_hours(knowledge: "LTSAKnowledge") -> float | None:
    values = [
        record.get("downtime_hours")
        for record in knowledge.cm_history
        if record.get("downtime_hours") is not None
    ]
    if not values:
        return None

    return mean(values)


def _compute_pm_compliance_rate(knowledge: "LTSAKnowledge", today: date) -> int:
    schedules = knowledge.pm_schedules
    if not schedules:
        return 0

    overdue = sum(1 for record in schedules if _is_overdue(record.get("next_due"), today))
    return round((len(schedules) - overdue) / len(schedules) * 100)


def _compute_critical_spare_count(knowledge: "LTSAKnowledge") -> int:
    return sum(1 for record in knowledge.inventory if _is_missing_stock(record.get("quantity_on_hand")))


def _is_missing_stock(quantity_on_hand: Any) -> bool:
    if quantity_on_hand is None:
        return True

    if isinstance(quantity_on_hand, str):
        value = quantity_on_hand.strip()
        if not value:
            return True
        try:
            quantity_on_hand = float(value)
        except ValueError:
            return True

    return quantity_on_hand <= 0


def _is_overdue(next_due: Any, today: date) -> bool:
    parsed = _parse_date(next_due)
    return parsed is not None and parsed < today


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


__all__ = ["ExecutiveMetrics", "compute_executive_metrics"]

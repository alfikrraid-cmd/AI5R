"""
MWO-LTSA-037B -- FleetReliabilityService: fleet-wide reliability rollup,
built entirely from three already-existing, reused building blocks --
PumpGateway.list_pumps() (which pumps exist), LTSAKnowledgeService.build()
(each pump's aggregate), and compute_executive_metrics() (each pump's KPI
set, MWO-LTSA-036N). No new gateway, no SQL, no API, no UI, no duplicate
calculation of any per-pump metric -- this service only aggregates values
compute_executive_metrics() already computed.

Aggregation rules, per metric:
  - fleet_health_score / fleet_mtbf_days / fleet_mttr_hours: mean across
    pumps that have a value (never fabricated for a pump with no data;
    None-safe, the same "skip missing, never invent zero" discipline
    compute_executive_metrics() itself already uses for mtbf_days/
    mttr_hours).
  - fleet_availability: derived from fleet_mtbf_days and fleet_mttr_hours
    via the standard reliability-engineering formula
    Availability = MTBF / (MTBF + MTTR), both converted to the same unit
    (days) before combining -- mtbf_days is already in days,
    fleet_mttr_hours is converted (/24) only for this one combination; the
    field itself stays in hours. No availability calculation exists
    anywhere else in the repository (confirmed by repository archaeology --
    "availability" elsewhere means spare-part stock_availability, an
    unrelated concept). None when either input is None -- never a
    fabricated ratio.
  - total_breakdown_count / total_critical_spare_count: sum across the
    fleet -- both are already raw per-pump counts in ExecutiveMetrics, so
    a fleet total is a sum, not a mean, matching how every other raw count
    in this codebase is totaled, not averaged.

Explicitly out of scope, per this MWO: no trend (no time-series, no
history-over-time) and no bad-actor ranking (no per-pump sort/worst-N
list) -- this service returns exactly one fleet-wide snapshot, nothing
more.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from .executive_metrics import ExecutiveMetrics, compute_executive_metrics
from .ltsa_knowledge_service import LTSAKnowledge, LTSAKnowledgeService
from .pump_area_scope import is_area_in_scope
from .pump_gateway import PumpGateway


@dataclass(frozen=True, slots=True)
class FleetReliability:
    """Immutable: one fleet-wide reliability snapshot across every pump.
    Fields with no supporting data are None, never fabricated."""

    pump_count: int
    fleet_health_score: float | None
    fleet_mtbf_days: float | None
    fleet_mttr_hours: float | None
    fleet_availability: float | None
    total_breakdown_count: int
    total_critical_spare_count: int


class FleetReliabilityService:
    """Aggregates compute_executive_metrics() across every pump in the
    registry into one FleetReliability snapshot. No new gateway, no SQL,
    no API, no UI -- pure aggregation over three already-existing, reused
    building blocks."""

    def __init__(
        self,
        pump_gateway: PumpGateway | None = None,
        ltsa_knowledge_service: LTSAKnowledgeService | None = None,
    ) -> None:
        self.pump_gateway = pump_gateway or PumpGateway()
        self.ltsa_knowledge_service = ltsa_knowledge_service or LTSAKnowledgeService()

    def build(self, *, scope: frozenset[str] | None = None) -> FleetReliability:
        # MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 -- scope is applied
        # HERE, at pump discovery, before any per-pump metric is even
        # computed -- never "compute the global result then hide pump
        # names". `scope=None` (the default) is the exact pre-existing
        # behavior for every caller that does not pass it (unrestricted
        # roles, and every existing test).
        #
        # MWO-LTSA-FLEET-ATTENTION-001 -- routed through list_pump_
        # knowledge()/aggregate_from_knowledge() (pure refactor, identical
        # result) so a caller that needs BOTH the aggregate AND per-pump
        # detail (FleetExecutiveSummaryService) can fetch knowledge once
        # and derive both from it, instead of this method independently
        # re-fetching the same per-pump knowledge a second time.
        return self.aggregate_from_knowledge(self.list_pump_knowledge(scope=scope))

    def aggregate_from_knowledge(self, knowledge: tuple[LTSAKnowledge, ...]) -> FleetReliability:
        """Pure aggregation, zero I/O -- the same compute_executive_metrics/
        _aggregate build() itself already used, just callable directly over
        already-fetched knowledge (MWO-LTSA-FLEET-ATTENTION-001)."""
        metrics = tuple(compute_executive_metrics(pump) for pump in knowledge)
        return self._aggregate(metrics)

    def list_pump_knowledge(self, *, scope: frozenset[str] | None = None) -> tuple[LTSAKnowledge, ...]:
        """MWO-LTSA-037E -- one LTSAKnowledge per pump in the registry,
        reusing the same pump discovery .build() already uses. Exists so
        callers that need per-pump detail (e.g. FleetExecutiveSummaryService,
        for Critical Assets / Top Risks -- both inherently per-pump) never
        have to re-implement pump discovery themselves."""
        tags = self._list_pump_tags(scope)
        return tuple(self.ltsa_knowledge_service.build(tag) for tag in tags)

    def _list_pump_tags(self, scope: frozenset[str] | None = None) -> tuple[str, ...]:
        # MWO-LTSA-037C runtime fix -- PumpGateway._call() only catches
        # urllib.error.HTTPError (an HTTP response with an error status);
        # a connection-level failure (refused/unreachable/timeout) raises
        # urllib.error.URLError, which is a direct OSError subclass and was
        # not caught anywhere on this path -- it propagated out of
        # .build() as an unhandled 500 instead of the same "no data
        # available" outcome every other gateway-failure case in this
        # codebase already degrades to (e.g. _build_pump's
        # success=False -> None). No pumps discovered is None-safe here
        # exactly like an empty registry already is -- not a new fallback
        # shape, the existing empty-fleet case.
        try:
            response = self.pump_gateway.list_pumps()
        except OSError:
            return ()
        records = response.get("data") or []
        if scope is not None:
            records = [r for r in records if is_area_in_scope(r.get("area"), scope)]
        return tuple(record.get("tag_number") for record in records if record.get("tag_number"))

    def _aggregate(self, metrics: tuple[ExecutiveMetrics, ...]) -> FleetReliability:
        fleet_mtbf_days = _mean_or_none(m.mtbf_days for m in metrics)
        fleet_mttr_hours = _mean_or_none(m.mttr_hours for m in metrics)

        return FleetReliability(
            pump_count=len(metrics),
            fleet_health_score=_mean_or_none(m.health_score for m in metrics),
            fleet_mtbf_days=fleet_mtbf_days,
            fleet_mttr_hours=fleet_mttr_hours,
            fleet_availability=_compute_availability(fleet_mtbf_days, fleet_mttr_hours),
            total_breakdown_count=sum(m.breakdown_count for m in metrics),
            total_critical_spare_count=sum(m.critical_spare_count for m in metrics),
        )


def _mean_or_none(values: Iterable[float | None]) -> float | None:
    known = [value for value in values if value is not None]
    if not known:
        return None
    return mean(known)


def _compute_availability(mtbf_days: float | None, mttr_hours: float | None) -> float | None:
    if mtbf_days is None or mttr_hours is None:
        return None

    mttr_days = mttr_hours / 24
    denominator = mtbf_days + mttr_days
    if denominator == 0:
        return None

    return round(mtbf_days / denominator * 100, 2)


__all__ = ["FleetReliability", "FleetReliabilityService"]

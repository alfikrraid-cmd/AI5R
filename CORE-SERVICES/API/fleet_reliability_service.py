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
        *,
        condition_monitoring_reading_repository=None,
        cm_report_repository=None,
        pm_occurrence_repository=None,
        pm_schedule_repository=None,
        seal_pump_compatibility_gateway=None,
        seal_gateway=None,
        mechanical_seal_stock_repository=None,
        work_order_gateway=None,
        maintenance_history_gateway=None,
    ) -> None:
        self.pump_gateway = pump_gateway or PumpGateway()
        self.ltsa_knowledge_service = ltsa_knowledge_service or LTSAKnowledgeService()
        # MWO-LTSA-FLEET-ANALYTICS-001 -- all optional, all None by
        # default: every existing caller/test that builds this service
        # with only pump_gateway/ltsa_knowledge_service (the pre-existing
        # two-arg constructor) gets the exact pre-existing behavior,
        # list_pump_knowledge_fast() falling back to list_pump_knowledge().
        # Only the production singleton in dependencies.py supplies these,
        # to actually collapse the fleet scan's per-pump gateway calls
        # down to one batch fetch (build_fleet_data_batch()).
        self.condition_monitoring_reading_repository = condition_monitoring_reading_repository
        self.cm_report_repository = cm_report_repository
        self.pm_occurrence_repository = pm_occurrence_repository
        self.pm_schedule_repository = pm_schedule_repository
        self.seal_pump_compatibility_gateway = seal_pump_compatibility_gateway
        self.seal_gateway = seal_gateway
        self.mechanical_seal_stock_repository = mechanical_seal_stock_repository
        self.work_order_gateway = work_order_gateway
        self.maintenance_history_gateway = maintenance_history_gateway

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
        return self.aggregate_from_knowledge(self.list_pump_knowledge_fast(scope=scope))

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

    def list_pump_knowledge_from_batch(self, batch: "FleetDataBatch") -> tuple[LTSAKnowledge, ...]:
        """MWO-LTSA-FLEET-ANALYTICS-001 -- pure, zero-I/O alternative to
        list_pump_knowledge(): builds the SAME LTSAKnowledge shape from an
        already-fetched FleetDataBatch (fleet_analytics_service.py) instead
        of calling ltsa_knowledge_service.build(tag) once per pump. This is
        the actual fix for "Pompa mana yang perlu perhatian hari ini?"'s
        own multi-minute latency: every field below was already redundantly
        refetched per pump by the OLD path; here every field is a plain
        dict lookup into data the caller fetched exactly once. Field-for-
        field equivalent to LTSAKnowledgeService.build()'s own shape except
        drawings/condition_monitoring_schedules/work_orders (empty tuples
        -- no existing RecommendationEngine rule reads them, so this never
        changes fleet ranking output, only how the inputs were fetched)."""
        knowledge: list[LTSAKnowledge] = []
        for pump in batch.pumps:
            tag = pump.get("tag_number")
            if not tag:
                continue
            inventory = [row for row in batch.stock_rows if row.get("equipment_tag") == tag]
            knowledge.append(
                LTSAKnowledge(
                    tag_number=tag,
                    pump=pump,
                    seal=list(batch.compatible_seals_by_tag.get(tag, ())),
                    inventory=inventory,
                    pm_history=list(batch.pm_by_tag.get(tag, ())),
                    cm_history=list(batch.cm_by_tag.get(tag, ())),
                    breakdown_history=list(batch.breakdown_by_tag.get(tag, ())),
                    drawings=[],
                    recommendation=(),
                    pm_schedules=list(batch.pm_schedule_by_tag.get(tag, ())),
                    condition_monitoring_schedules=[],
                    condition_monitoring_readings=list(batch.cmon_by_tag.get(tag, ())),
                )
            )
        return tuple(knowledge)

    def _batch_sources_available(self) -> bool:
        """MWO-LTSA-FLEET-ANALYTICS-001 -- true only when every REQUIRED
        batch-fetch dependency (mirrors build_fleet_data_batch()'s own
        required, non-optional keyword args) was supplied at construction.
        work_order_gateway/maintenance_history_gateway stay optional here
        too (breakdown_history coverage, not required for the batch path
        itself to run)."""
        return all(
            [
                self.condition_monitoring_reading_repository,
                self.cm_report_repository,
                self.pm_occurrence_repository,
                self.pm_schedule_repository,
                self.seal_pump_compatibility_gateway,
                self.seal_gateway,
                self.mechanical_seal_stock_repository,
            ]
        )

    def list_pump_knowledge_fast(self, *, scope: frozenset[str] | None = None) -> tuple[LTSAKnowledge, ...]:
        """MWO-LTSA-FLEET-ANALYTICS-001 -- the actual fix for "Pompa mana
        yang perlu perhatian hari ini?"'s own multi-minute latency: when
        this service was constructed with the batch-sourcing dependencies
        (see dependencies.py's production singleton wiring), fetches every
        data source EXACTLY ONCE via build_fleet_data_batch() and derives
        per-pump knowledge from it with zero further I/O. Falls back to
        the original list_pump_knowledge() (one gateway round trip per
        pump) when those dependencies are absent, so every existing
        caller/test that builds this service with only pump_gateway/
        ltsa_knowledge_service keeps its exact current behavior -- this
        method is purely additive, never a behavior change for them."""
        if not self._batch_sources_available():
            return self.list_pump_knowledge(scope=scope)
        from .fleet_analytics_service import build_fleet_data_batch

        batch = build_fleet_data_batch(
            pump_gateway=self.pump_gateway,
            condition_monitoring_reading_repository=self.condition_monitoring_reading_repository,
            cm_report_repository=self.cm_report_repository,
            pm_occurrence_repository=self.pm_occurrence_repository,
            pm_schedule_repository=self.pm_schedule_repository,
            seal_pump_compatibility_gateway=self.seal_pump_compatibility_gateway,
            seal_gateway=self.seal_gateway,
            mechanical_seal_stock_repository=self.mechanical_seal_stock_repository,
            work_order_gateway=self.work_order_gateway,
            maintenance_history_gateway=self.maintenance_history_gateway,
            scope=scope,
        )
        return self.list_pump_knowledge_from_batch(batch)

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

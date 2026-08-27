"""
MWO-LTSA-031F / R1 -- RecommendationEngine: deterministic, rule-based
recommendations over an already-built LTSAKnowledge aggregate
(MWO-LTSA-031A). No LLM, no AI reasoning, no gateway/SQL/API/Router
access of its own -- pure business rules over data the caller already
assembled.

--------------------------------------------------------------------------
MWO-LTSA-ENGINEERING-AI-CMON-REASONING-020B (this revision)
--------------------------------------------------------------------------
Fixes 4 confirmed defects from MWO-020A's audit, all still pure functions
of already-assembled data -- no gateway, no SQL, no LLM added anywhere:

1. CMON/leak evidence never influenced recommendation selection. `summary`
   (EngineeringContextEngine.build()'s own already-computed, already
   evidence-cited output -- cm_summary.leak_flag/latest_abnormal_values,
   pm_summary.status, per that module's own _build_cm_summary/
   _build_pm_summary) is now an optional second argument to recommend()
   and every rule -- reused verbatim, never re-derived. New
   _check_active_leak reads cm_summary.leak_flag (already windowed,
   already evidence-cited) at priority 95, between REC_CRITICAL_CM (100)
   and the existing HIGH tier (90) -- an active leak now outranks a
   generic PM recommendation.

2. REC_PM_OVERDUE no longer treats "no PM history" as overdue. It now
   reads summary.pm_summary.status (EngineeringContextEngine's own
   already-computed PLANNED/ACTIVE/OVERDUE/DUE_SOON/UNSCHEDULED lifecycle,
   MWO-LTSA-016/016A, untouched) and only fires on real OVERDUE/DUE_SOON
   schedule evidence, cited from summary.evidence's own PM_OVERDUE flag.
   No summary, or no schedule evidence -> no PM recommendation at all
   (the caller's insight becomes DATA_GAP if nothing else fires) -- never
   a guessed "overdue".

3. Historical leak evidence (any point in
   knowledge.condition_monitoring_readings, no time window -- the full,
   already-fetched list, no new query) is surfaced by a new,
   low-priority, purely informational _check_historical_leak_evidence
   rule whenever the CURRENT window (cm_summary.leak_flag) is False --
   so a pump with real past leak evidence is never represented as if no
   leak history exists, while a current/active leak is never confused
   with a merely historical one (the two rules are mutually exclusive by
   construction: historical only fires when leak_flag is False).

4. REC_NO_STOCK now reads quantity_available (Stock V1's own authoritative
   "available" field, MWO-LTSA-AI-COPILOT-FLEET-STOCK-V1-017B's own
   established convention), not quantity_on_hand. Priority lowered to 60
   (below the new PM-due tier), per this MWO's own explicit rule
   ordering.

Priority tiers (matches this MWO's own suggested ordering exactly, no
deviation): critical confirmed CM (100) > active leak (95) > other
existing failure/breakdown rules -- REC_REPEATED_BREAKDOWN and
REC_SEAL_FAILURE, both already-filed/human-confirmed CM-report-based
signals, kept at their pre-existing priority (90) > PM due/overdue, now
evidence-based (80) > stock constraint (60) > historical leak evidence,
informational only (40) > no match -> DATA_GAP. Active leak (95)
numerically outranks REC_SEAL_FAILURE/REC_REPEATED_BREAKDOWN (90) --
this is the mission's own requested "current leak > other
failure/breakdown rules" ordering, applied as-is, not a deviation from
it. Active leak also outranks the PM/stock/historical tiers, satisfying
"active leak outranks generic PM" exactly as required.

Reuse before create (unchanged from the original MWO): LTSAKnowledge is
imported unchanged from ltsa_knowledge_service.py, not redefined. The CM
"CRITICAL" definition and "missing stock" definition are still mirrored
from EngineeringContextEngine's own established rules, not reinvented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # MWO-LTSA-032C: ltsa_knowledge_service.py now imports RecommendationEngine
    # (constructor injection), so a module-level import here would be
    # circular. LTSAKnowledge is used only as a type hint, never at
    # runtime, and `from __future__ import annotations` (above) already
    # defers all annotation evaluation -- TYPE_CHECKING-gating this import
    # is a pure import-timing fix, not a change to any rule's behavior.
    from .ltsa_knowledge_service import LTSAKnowledge

CRITICAL_CM_SEVERITIES = {"MAJOR", "CRITICAL"}
OPEN_CM_STATUSES = {"OPEN", "IN_PROGRESS"}

DEFAULT_REPEATED_BREAKDOWN_THRESHOLD = 2

ALLOWED_CATEGORIES = frozenset({"MAINTENANCE", "RELIABILITY", "SPARE_PART", "INSPECTION"})

PRIORITY_CRITICAL = 100
PRIORITY_ACTIVE_LEAK = 95
PRIORITY_HIGH = 90
PRIORITY_PM_DUE = 80
PRIORITY_STOCK = 60
PRIORITY_HISTORICAL_LEAK = 40

# PM due/overdue confidence: OVERDUE is a real, unambiguous elapsed-time
# fact (schedule.next_due < today) -- confidence 1.0. DUE_SOON is real
# evidence too but a softer signal (approaching, not yet passed) --
# confidence 0.8, disclosed as such, never presented as equally certain.
PM_OVERDUE_CONFIDENCE = 1.0
PM_DUE_SOON_CONFIDENCE = 0.8


@dataclass(frozen=True, slots=True)
class Evidence:
    """Immutable: one cited data point supporting a Recommendation. No
    canonical Evidence object existed anywhere in the repository prior
    to this MWO (confirmed by repository-wide archaeology)."""

    source: str
    reference: str
    field: str
    value: str


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Immutable: one deterministic recommendation produced by a single
    rule. id is always f"{rule_code}:{tag_number}" -- never a UUID,
    never random."""

    id: str
    rule_code: str
    priority: int
    category: str
    title: str
    description: str
    evidence: tuple[Evidence, ...]
    confidence: float
    action: str

    def __post_init__(self) -> None:
        if self.category not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(ALLOWED_CATEGORIES)}: got {self.category!r}")


class RecommendationEngine:
    """Deterministic, rule-based recommendations over LTSAKnowledge (and,
    since MWO-020B, the already-built EngineeringContextEngine summary).
    No LLM, no AI reasoning -- every rule is a pure function of already-
    assembled data. Thresholds are constructor-injected (dependency
    injection), not hardcoded magic numbers."""

    def __init__(self, repeated_breakdown_threshold: int = DEFAULT_REPEATED_BREAKDOWN_THRESHOLD) -> None:
        if repeated_breakdown_threshold < 1:
            raise ValueError("repeated_breakdown_threshold must be a positive integer")
        self._repeated_breakdown_threshold = repeated_breakdown_threshold

    def recommend(
        self, knowledge: LTSAKnowledge, summary: dict[str, Any] | None = None
    ) -> tuple[Recommendation, ...]:
        # `summary` is optional (default None) so every pre-existing
        # caller that only ever had LTSAKnowledge (LTSAKnowledgeService.
        # build() itself, and Copilot's own recommendation intent) keeps
        # working unchanged, at the pre-020B recommendation set; passing
        # summary is what unlocks the CMON/leak- and PM-schedule-aware
        # rules below. See routers/engineering_ai.py for the one caller
        # that now supplies it.
        checks = (
            self._check_critical_cm,
            self._check_active_leak,
            self._check_repeated_breakdown,
            self._check_seal_leakage,
            self._check_pm_due,
            self._check_zero_inventory,
            self._check_historical_leak_evidence,
        )
        found = tuple(rec for rec in (check(knowledge, summary) for check in checks) if rec is not None)
        # Sort by priority descending; Python's sort is stable, so ties
        # keep the fixed rule-evaluation order above -- output stays
        # fully deterministic.
        return tuple(sorted(found, key=lambda rec: rec.priority, reverse=True))

    # -- rules (isolated, independently callable; `summary` optional/unused
    # by rules that do not need it, kept for a uniform call signature) ----

    def _check_pm_due(
        self, knowledge: LTSAKnowledge, summary: dict[str, Any] | None = None
    ) -> Recommendation | None:
        pm_summary = (summary or {}).get("pm_summary") or {}
        status = pm_summary.get("status")
        if status not in ("OVERDUE", "DUE_SOON"):
            return None

        schedule_evidence = next(
            (
                item
                for item in (summary or {}).get("evidence") or []
                if item.get("flag") == "PM_OVERDUE"
            ),
            None,
        )
        # OVERDUE without its own cited evidence entry would be an
        # internal inconsistency in the already-built summary -- never
        # fabricate a recommendation without a real citation to point to.
        if status == "OVERDUE" and schedule_evidence is None:
            return None

        evidence: tuple[Evidence, ...]
        if schedule_evidence is not None:
            evidence = (
                Evidence(
                    source=schedule_evidence.get("source", "PMSchedule"),
                    reference=str(schedule_evidence.get("reference")),
                    field="status",
                    value=status,
                ),
            )
        else:
            # DUE_SOON has no dedicated flag in summary.evidence today
            # (only OVERDUE/NO_ACTIVE_PM are flagged there) -- cite the
            # pm_summary.status field itself rather than inventing a
            # reference this module cannot support.
            evidence = (Evidence(source="PMSchedule", reference=knowledge.tag_number, field="status", value=status),)

        if status == "OVERDUE":
            description = "The PM schedule's next due date has passed (status: OVERDUE)."
            confidence = PM_OVERDUE_CONFIDENCE
            action = "Schedule a preventive maintenance visit."
        else:
            description = "The PM schedule's next due date is approaching (status: DUE_SOON)."
            confidence = PM_DUE_SOON_CONFIDENCE
            action = "Schedule a preventive maintenance visit soon."

        return Recommendation(
            id=f"REC_PM_OVERDUE:{knowledge.tag_number}",
            rule_code="REC_PM_OVERDUE",
            priority=PRIORITY_PM_DUE,
            category="MAINTENANCE",
            title="Schedule PM",
            description=description,
            evidence=evidence,
            confidence=confidence,
            action=action,
        )

    def _check_critical_cm(
        self, knowledge: LTSAKnowledge, summary: dict[str, Any] | None = None
    ) -> Recommendation | None:
        evidence = tuple(
            Evidence(source="CMReport", reference=record["cm_report_code"], field="severity", value=record["severity"])
            for record in knowledge.cm_history
            if record.get("severity") in CRITICAL_CM_SEVERITIES and record.get("status") in OPEN_CM_STATUSES
        )
        if not evidence:
            return None

        return Recommendation(
            id=f"REC_CRITICAL_CM:{knowledge.tag_number}",
            rule_code="REC_CRITICAL_CM",
            priority=PRIORITY_CRITICAL,
            category="INSPECTION",
            title="Immediate Inspection",
            description="An open Corrective Maintenance report with critical or major severity was found.",
            evidence=evidence,
            confidence=1.0,
            action="Dispatch a technician for immediate inspection.",
        )

    def _check_active_leak(
        self, knowledge: LTSAKnowledge, summary: dict[str, Any] | None = None
    ) -> Recommendation | None:
        cm_summary = (summary or {}).get("cm_summary") or {}
        if not cm_summary.get("leak_flag"):
            return None

        latest = cm_summary.get("latest_abnormal_values") or {}
        evidence = tuple(
            Evidence(
                source="ConditionMonitoringReading",
                reference=str(latest.get("reading_code") or knowledge.tag_number),
                field=field_name,
                value="True",
            )
            for field_name in ("mechanical_seal_leak_de", "mechanical_seal_leak_nde")
            if latest.get(field_name) is True
        )
        if not evidence:
            # leak_flag true but no per-side detail available -- still a
            # real, already-computed flag; cite the flag itself rather
            # than inventing which side leaked.
            evidence = (
                Evidence(
                    source="ConditionMonitoringReading",
                    reference=str(latest.get("reading_code") or knowledge.tag_number),
                    field="leak_flag",
                    value="True",
                ),
            )

        return Recommendation(
            id=f"REC_ACTIVE_LEAK:{knowledge.tag_number}",
            rule_code="REC_ACTIVE_LEAK",
            priority=PRIORITY_ACTIVE_LEAK,
            category="INSPECTION",
            title="Active Seal Leak Detected",
            description=(
                "A mechanical seal leak was recorded in condition monitoring readings "
                "within the current active-monitoring window."
            ),
            evidence=evidence,
            confidence=1.0,
            action="Inspect the mechanical seal for active leakage.",
        )

    def _check_repeated_breakdown(
        self, knowledge: LTSAKnowledge, summary: dict[str, Any] | None = None
    ) -> Recommendation | None:
        if len(knowledge.breakdown_history) < self._repeated_breakdown_threshold:
            return None

        evidence = tuple(
            Evidence(
                source="MaintenanceHistory",
                reference=record["maintenance_record_code"],
                field="maintenance_record_code",
                value=record["maintenance_record_code"],
            )
            for record in knowledge.breakdown_history
        )

        return Recommendation(
            id=f"REC_REPEATED_BREAKDOWN:{knowledge.tag_number}",
            rule_code="REC_REPEATED_BREAKDOWN",
            priority=PRIORITY_HIGH,
            category="RELIABILITY",
            title="Root Cause Analysis",
            description=f"{len(evidence)} breakdown-linked maintenance records were found for this pump.",
            evidence=evidence,
            confidence=1.0,
            action="Initiate a root cause analysis investigation.",
        )

    def _check_zero_inventory(
        self, knowledge: LTSAKnowledge, summary: dict[str, Any] | None = None
    ) -> Recommendation | None:
        evidence = tuple(
            Evidence(
                source="MechanicalSealStockV1",
                reference=record.get("stock_pool_id") or record.get("seal_code") or knowledge.tag_number,
                field="quantity_available",
                value=str(record.get("quantity_available")),
            )
            for record in knowledge.inventory
            if _is_missing_stock(record.get("quantity_available"))
        )
        if not evidence:
            return None

        return Recommendation(
            id=f"REC_NO_STOCK:{knowledge.tag_number}",
            rule_code="REC_NO_STOCK",
            priority=PRIORITY_STOCK,
            category="SPARE_PART",
            title="Procurement Required",
            description="One or more compatible spare parts have no confirmed stock available.",
            evidence=evidence,
            confidence=1.0,
            action="Initiate procurement for the affected spare part(s).",
        )

    def _check_seal_leakage(
        self, knowledge: LTSAKnowledge, summary: dict[str, Any] | None = None
    ) -> Recommendation | None:
        evidence = tuple(
            Evidence(source="CMReport", reference=record["cm_report_code"], field="failure_category", value="SEAL_FAILURE")
            for record in knowledge.cm_history
            if record.get("failure_category") == "SEAL_FAILURE"
        )
        if not evidence:
            return None

        return Recommendation(
            id=f"REC_SEAL_FAILURE:{knowledge.tag_number}",
            rule_code="REC_SEAL_FAILURE",
            priority=PRIORITY_HIGH,
            category="INSPECTION",
            title="Inspect Mechanical Seal",
            description="A Corrective Maintenance report categorized as seal failure was found.",
            evidence=evidence,
            confidence=1.0,
            action="Inspect the mechanical seal for leakage.",
        )

    def _check_historical_leak_evidence(
        self, knowledge: LTSAKnowledge, summary: dict[str, Any] | None = None
    ) -> Recommendation | None:
        # Mutually exclusive with _check_active_leak by construction: only
        # considered when the CURRENT window shows no active leak, so a
        # pump is never given two competing leak claims at once, and a
        # historical-only reading is never described as "active".
        cm_summary = (summary or {}).get("cm_summary") or {}
        if cm_summary.get("leak_flag"):
            return None

        historical = tuple(
            Evidence(
                source="ConditionMonitoringReading",
                reference=str(record.get("condition_monitoring_reading_code") or knowledge.tag_number),
                field="mechanical_seal_leak_de" if record.get("mechanical_seal_leak_de") is True else "mechanical_seal_leak_nde",
                value="True",
            )
            for record in knowledge.condition_monitoring_readings
            if record.get("mechanical_seal_leak_de") is True or record.get("mechanical_seal_leak_nde") is True
        )
        if not historical:
            return None

        return Recommendation(
            id=f"REC_HISTORICAL_LEAK:{knowledge.tag_number}",
            rule_code="REC_HISTORICAL_LEAK",
            priority=PRIORITY_HISTORICAL_LEAK,
            category="RELIABILITY",
            title="Historical Seal Leak Evidence",
            description=(
                f"{len(historical)} historical condition monitoring reading(s) recorded a mechanical "
                "seal leak outside the current active-monitoring window."
            ),
            evidence=historical,
            confidence=1.0,
            action="Review historical leak trend at the next scheduled inspection.",
        )


def _is_missing_stock(quantity_available: Any) -> bool:
    if quantity_available is None:
        return True

    if isinstance(quantity_available, str):
        value = quantity_available.strip()
        if not value:
            return True
        try:
            quantity_available = float(value)
        except ValueError:
            return True

    return quantity_available <= 0


__all__ = ["Evidence", "Recommendation", "RecommendationEngine"]

"""
MWO-LTSA-031F / R1 -- RecommendationEngine: deterministic, rule-based
recommendations over an already-built LTSAKnowledge aggregate
(MWO-LTSA-031A). No LLM, no AI reasoning, no gateway/SQL/API/Router
access of its own -- pure business rules over data the caller already
assembled.

R1 refinement (canonical promotion, no new rules, no redesign):
  - Every Recommendation carries a stable rule_code (REC_PM_OVERDUE,
    REC_CRITICAL_CM, REC_REPEATED_BREAKDOWN, REC_NO_STOCK,
    REC_SEAL_FAILURE).
  - id is now deterministic: f"{rule_code}:{tag_number}" -- no UUID, no
    randomness (previously f"REC-{tag}-{SLUG}", same determinism
    property, new canonical format per Chief Architect directive).
  - evidence is now a tuple of Evidence objects (source, reference,
    field, value), not bare strings -- repository archaeology (this
    MWO) confirmed no canonical Evidence class exists anywhere in the
    repository, so one was created here rather than reused; "source"
    values (CMReport, SealStock) reuse the exact vocabulary
    EngineeringContextEngine's own evidence dicts already use for the
    same underlying records, not invented fresh.
  - priority is now an int (100/90/70 -- three tiers, one per distinct
    urgency level actually needed by these five rules; the two-of-five
    rules that were already tied at "HIGH" stay tied at 90, since nothing
    in this MWO asked for finer-grained distinctions between them).
    recommend() now sorts its output by priority, descending; Python's
    sort is stable, so equal-priority recommendations keep their fixed
    rule-evaluation order -- output remains fully deterministic.
  - category is now drawn from the canonical four-value set (MAINTENANCE,
    RELIABILITY, SPARE_PART, INSPECTION), replacing the previous five
    domain-specific labels (PM/CM/RELIABILITY/INVENTORY/SEAL).

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
PM_OVERDUE_CONFIDENCE = 0.6

ALLOWED_CATEGORIES = frozenset({"MAINTENANCE", "RELIABILITY", "SPARE_PART", "INSPECTION"})

PRIORITY_CRITICAL = 100
PRIORITY_HIGH = 90
PRIORITY_MEDIUM = 70


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
    """Deterministic, rule-based recommendations over LTSAKnowledge. No
    LLM, no AI reasoning -- every rule is a pure function of already-
    assembled data. Thresholds are constructor-injected (dependency
    injection), not hardcoded magic numbers."""

    def __init__(self, repeated_breakdown_threshold: int = DEFAULT_REPEATED_BREAKDOWN_THRESHOLD) -> None:
        if repeated_breakdown_threshold < 1:
            raise ValueError("repeated_breakdown_threshold must be a positive integer")
        self._repeated_breakdown_threshold = repeated_breakdown_threshold

    def recommend(self, knowledge: LTSAKnowledge) -> tuple[Recommendation, ...]:
        checks = (
            self._check_pm_overdue,
            self._check_critical_cm,
            self._check_repeated_breakdown,
            self._check_zero_inventory,
            self._check_seal_leakage,
        )
        found = tuple(rec for rec in (check(knowledge) for check in checks) if rec is not None)
        # Sort by priority descending; Python's sort is stable, so ties
        # keep the fixed rule-evaluation order above -- output stays
        # fully deterministic.
        return tuple(sorted(found, key=lambda rec: rec.priority, reverse=True))

    # -- rules (isolated, independently callable) ----------------------------

    def _check_pm_overdue(self, knowledge: LTSAKnowledge) -> Recommendation | None:
        # Temporary heuristic. Replace when LTSAKnowledge exposes PM Schedule.
        # Do not change runtime behavior (Chief Architect directive,
        # MWO-LTSA-031F-R1): this still fires purely on "zero PM
        # Occurrence history exists" and nothing else.
        if knowledge.pm_history:
            return None

        return Recommendation(
            id=f"REC_PM_OVERDUE:{knowledge.tag_number}",
            rule_code="REC_PM_OVERDUE",
            priority=PRIORITY_MEDIUM,
            category="MAINTENANCE",
            title="Schedule PM",
            description="No preventive maintenance history found for this pump.",
            evidence=(),
            confidence=PM_OVERDUE_CONFIDENCE,
            action="Schedule a preventive maintenance visit.",
        )

    def _check_critical_cm(self, knowledge: LTSAKnowledge) -> Recommendation | None:
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

    def _check_repeated_breakdown(self, knowledge: LTSAKnowledge) -> Recommendation | None:
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

    def _check_zero_inventory(self, knowledge: LTSAKnowledge) -> Recommendation | None:
        evidence = tuple(
            Evidence(
                source="SealStock",
                reference=record["seal_code"],
                field="quantity_on_hand",
                value=str(record.get("quantity_on_hand")),
            )
            for record in knowledge.inventory
            if _is_missing_stock(record.get("quantity_on_hand"))
        )
        if not evidence:
            return None

        return Recommendation(
            id=f"REC_NO_STOCK:{knowledge.tag_number}",
            rule_code="REC_NO_STOCK",
            priority=PRIORITY_HIGH,
            category="SPARE_PART",
            title="Procurement Required",
            description="One or more compatible spare parts have no confirmed stock on hand.",
            evidence=evidence,
            confidence=1.0,
            action="Initiate procurement for the affected spare part(s).",
        )

    def _check_seal_leakage(self, knowledge: LTSAKnowledge) -> Recommendation | None:
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


__all__ = ["Evidence", "Recommendation", "RecommendationEngine"]

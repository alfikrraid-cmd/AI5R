"""MWO-LTSA-SEAL-LEAK-DIAGNOSTIC-001 -- CORE evidence-based mechanical-seal
leak diagnostic engine. Reuses existing canonical sources only:
LTSAKnowledgeService.build(tag) (seal compatibility/inventory/PM/CM/
breakdown/CMON history), EquipmentTimelineService.build_current_seal(tag)
(confirmed installed seal), maintenance_intelligence_service.
leak_flag_from_readings (same 30-day active-leak window RecommendationEngine
and fleet_analytics_service already use), and recommendation_engine's own
DEFAULT_REPEATED_BREAKDOWN_THRESHOLD (canonical, not invented here).

Hard rules (never violated):
  - No LLM is a source of fact; every field below is deterministic.
  - Missing evidence stays DATA_GAP, never coerced to zero/false.
  - No invented temperature/vibration/pressure thresholds -- raw values
    and simple direction-of-change trends only, never HIGH/ABNORMAL.
  - `conclusion` is NEVER "CONFIRMED_ROOT_CAUSE" in this CORE engine -- no
    deterministic confirmation rule is defined at this evidence
    granularity; always PROBABLE_CAUSE / INSUFFICIENT_EVIDENCE /
    NO_LEAK_EVIDENCE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from . import maintenance_intelligence_service as mis
from .condition_monitoring_measurement_fields import fields_matching_search_term, parameter_values
from .recommendation_engine import DEFAULT_REPEATED_BREAKDOWN_THRESHOLD

HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

DATA_GAP = "DATA_GAP"

STATUS_LEAK_CURRENT = "LEAK_EVIDENCE_CURRENT"
STATUS_LEAK_HISTORICAL = "LEAK_EVIDENCE_HISTORICAL_ONLY"
STATUS_NO_LEAK = "NO_LEAK_EVIDENCE"

STOCK_AVAILABLE = "AVAILABLE"
STOCK_ZERO = "ZERO_STOCK"
STOCK_NO_RECORD = "NO_STOCK_RECORD"
STOCK_NO_COMPATIBLE_SEAL = "NO_COMPATIBLE_SEAL"

CONCLUSION_PROBABLE_CAUSE = "PROBABLE_CAUSE"
CONCLUSION_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
CONCLUSION_NO_LEAK_EVIDENCE = "NO_LEAK_EVIDENCE"

_INSTALLATION_RECENCY_DAYS = 90
_CONTAMINATION_KEYWORDS = ("contamina", "abrasive", "kotor", "debris", "particle")
_ALIGNMENT_KEYWORDS = ("alignment", "shaft", "bearing", "misalign")


@dataclass(frozen=True, slots=True)
class Hypothesis:
    cause: str
    confidence: str
    supporting_evidence: tuple[str, ...]
    missing_or_contradicting_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StockReadinessRow:
    seal_code: str | None
    seal_model: str | None
    size: str | None
    quantity: int | None
    state: str


@dataclass(frozen=True, slots=True)
class SealLeakDiagnosis:
    equipment: str
    diagnostic_status: str
    leak_evidence: dict[str, Any]
    temperature_evidence: dict[str, Any]
    vibration_evidence: dict[str, Any]
    operating_evidence: dict[str, Any]
    maintenance_evidence: dict[str, Any]
    seal_evidence: dict[str, Any]
    inventory_evidence: tuple[StockReadinessRow, ...]
    hypotheses: tuple[Hypothesis, ...]
    recommended_checks: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    confidence: str
    conclusion: str


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _is_leak_flagged(record: dict[str, Any]) -> bool:
    return record.get("mechanical_seal_leak_de") is True or record.get("mechanical_seal_leak_nde") is True


# -- DETECT + COLLECT: leak evidence ------------------------------------------


def _collect_leak_evidence(readings: list[dict[str, Any]], *, today: date) -> tuple[dict[str, Any], bool, int]:
    current = mis.leak_flag_from_readings(list(readings), today=today)
    cutoff = today - timedelta(days=mis.DEFAULT_CONDITION_MONITORING_WINDOW_DAYS)
    historical = [
        r for r in readings
        if _is_leak_flagged(r) and (lambda d: d is not None and d < cutoff)(_parse_date(r.get("reading_date")))
    ]
    evidence = {
        "current_leak_flag": current["flagged"],
        "latest_leak_finding": None,
        "historical_leak_count": len(historical),
    }
    if current["flagged"] and current.get("latest_flagged_reading"):
        rec = current["latest_flagged_reading"]
        evidence["latest_leak_finding"] = {
            "reading_date": rec.get("reading_date"),
            "finding": rec.get("finding"),
            "workflow_status": rec.get("workflow_status"),
            "source": rec.get("condition_monitoring_reading_code"),
        }
    return evidence, bool(current["flagged"]), len(historical)


# -- COLLECT: temperature / vibration / operating state -----------------------


def _collect_parameter_evidence(latest: dict[str, Any] | None, previous: dict[str, Any] | None, term: str) -> dict[str, Any]:
    if latest is None:
        return {"status": DATA_GAP}
    fields = fields_matching_search_term(term)
    values = parameter_values(latest, fields)
    if not values:
        return {"status": DATA_GAP}
    readings = [{"label": label, "value": value, "unit": unit} for label, value, unit in values]
    trend = None
    if previous is not None:
        prev_values = {label: value for label, value, _unit in parameter_values(previous, fields)}
        deltas = {}
        for label, value, _unit in values:
            if label in prev_values:
                if value > prev_values[label]:
                    deltas[label] = "increasing"
                elif value < prev_values[label]:
                    deltas[label] = "decreasing"
                else:
                    deltas[label] = "unchanged"
        trend = deltas or None
    return {"status": "FACT", "reading_date": latest.get("reading_date"), "readings": readings, "trend": trend}


def _collect_operating_evidence(latest: dict[str, Any] | None, pump: dict[str, Any] | None) -> dict[str, Any]:
    state = latest.get("pump_operating_state") if latest else None
    area_status = (pump or {}).get("status")
    if state is None and area_status is None:
        return {"status": DATA_GAP}
    return {"status": "FACT", "operating_state": state, "pump_status": area_status}


# -- COLLECT: seal identity + inventory readiness ------------------------------


def _collect_seal_evidence(compatible_seals: list[dict[str, Any]], installed_seal: Any) -> dict[str, Any]:
    installed = None
    if installed_seal is not None and getattr(installed_seal, "seal_code", None):
        installed = {
            "seal_code": installed_seal.seal_code,
            "seal_name": installed_seal.seal_name,
            "installed_at": installed_seal.installed_at,
            "status": installed_seal.status,
        }
    return {
        "confirmed_installed_seal": installed if installed is not None else DATA_GAP,
        "compatible_seals": [
            {"seal_code": s.get("seal_code"), "part_name": s.get("part_name")} for s in compatible_seals
        ],
    }


def _classify_stock(compatible_seals: list[dict[str, Any]], inventory_rows: list[dict[str, Any]]) -> tuple[StockReadinessRow, ...]:
    if not compatible_seals:
        return (StockReadinessRow(None, None, None, None, STOCK_NO_COMPATIBLE_SEAL),)
    by_seal_type: dict[str, dict[str, Any]] = {}
    for row in inventory_rows:
        key = (row.get("seal_type") or "").upper()
        if key:
            by_seal_type[key] = row
    results: list[StockReadinessRow] = []
    for seal in compatible_seals:
        code = seal.get("seal_code")
        row = by_seal_type.get((code or "").upper())
        if row is None or row.get("quantity_available") is None:
            results.append(StockReadinessRow(code, seal.get("part_name"), None, None, STOCK_NO_RECORD))
        elif row["quantity_available"] == 0:
            size = f"{row.get('nominal_size')} {row.get('size_unit')}".strip() if row.get("nominal_size") else None
            results.append(StockReadinessRow(code, row.get("seal_type"), size, 0, STOCK_ZERO))
        else:
            size = f"{row.get('nominal_size')} {row.get('size_unit')}".strip() if row.get("nominal_size") else None
            results.append(StockReadinessRow(code, row.get("seal_type"), size, row["quantity_available"], STOCK_AVAILABLE))
    return tuple(results)


# -- HYPOTHESIZE ---------------------------------------------------------------


def _build_hypotheses(
    *,
    has_leak_evidence: bool,
    current_leak: bool,
    historical_leak_count: int,
    breakdown_count: int,
    seal_failure_cm: bool,
    temperature_evidence: dict[str, Any],
    vibration_evidence: dict[str, Any],
    leak_findings_text: list[str],
    seal_evidence: dict[str, Any],
    latest_leak_reading_date: date | None,
) -> tuple[Hypothesis, ...]:
    if not has_leak_evidence:
        return ()

    hypotheses: list[Hypothesis] = []
    repeated_breakdown = breakdown_count >= DEFAULT_REPEATED_BREAKDOWN_THRESHOLD
    signals = sum([True, repeated_breakdown, seal_failure_cm])  # leak evidence itself is always signal #1
    confidence = HIGH if signals >= 3 else MEDIUM if signals == 2 else LOW

    supporting = ["Mechanical seal leak evidence recorded in condition monitoring readings"]
    if repeated_breakdown:
        supporting.append(f"Repeated breakdown history ({breakdown_count} record(s), >= canonical threshold {DEFAULT_REPEATED_BREAKDOWN_THRESHOLD})")
    if seal_failure_cm:
        supporting.append("Corrective Maintenance report with failure_category=SEAL_FAILURE on record")
    missing = []
    if not repeated_breakdown:
        missing.append("No repeated breakdown history corroborating seal degradation")
    if not seal_failure_cm:
        missing.append("No confirmed CM seal-failure report on record")
    hypotheses.append(Hypothesis("seal_face_or_secondary_seal_degradation", confidence, tuple(supporting), tuple(missing)))

    if temperature_evidence.get("status") == "FACT":
        flush_labels = [r["label"] for r in temperature_evidence["readings"] if "flush" in r["label"].lower() or "cooling" in r["label"].lower() or "quench" in r["label"].lower()]
        if flush_labels:
            hypotheses.append(Hypothesis(
                "inadequate_flush_cooling_lubrication", LOW,
                (f"Flush/cooling/quench temperature data present alongside leak evidence: {', '.join(flush_labels)}",),
                ("No canonical flush pressure/temperature threshold available to assess adequacy",),
            ))

    if vibration_evidence.get("status") == "FACT":
        hypotheses.append(Hypothesis(
            "alignment_shaft_movement_bearing_related", LOW,
            ("Vibration readings present alongside leak evidence",),
            ("No canonical vibration threshold/baseline available to assess severity",),
        ))
    elif any(any(kw in (t or "").lower() for kw in _ALIGNMENT_KEYWORDS) for t in leak_findings_text):
        hypotheses.append(Hypothesis(
            "alignment_shaft_movement_bearing_related", LOW,
            ("CMON finding text references alignment/shaft/bearing",),
            ("No vibration readings recorded for this equipment",),
        ))
    else:
        hypotheses.append(Hypothesis(
            "alignment_shaft_movement_bearing_related", INSUFFICIENT_EVIDENCE,
            (), ("No vibration readings recorded for this equipment",),
        ))

    if any(any(kw in (t or "").lower() for kw in _CONTAMINATION_KEYWORDS) for t in leak_findings_text):
        hypotheses.append(Hypothesis(
            "contamination_or_abrasive_wear", LOW,
            ("CMON finding text references contamination/abrasive/debris",),
            ("No particle/contamination analysis evidence available in canonical data",),
        ))

    installed = seal_evidence.get("confirmed_installed_seal")
    if isinstance(installed, dict) and installed.get("installed_at") and latest_leak_reading_date is not None:
        installed_at = _parse_date(installed["installed_at"])
        if installed_at is not None and 0 <= (latest_leak_reading_date - installed_at).days <= _INSTALLATION_RECENCY_DAYS:
            hypotheses.append(Hypothesis(
                "installation_or_assembly_issue", LOW,
                (f"Leak evidence recorded within {_INSTALLATION_RECENCY_DAYS} days of confirmed seal installation ({installed['installed_at']})",),
                ("No installation report inspection/torque/fitment record evaluated here",),
            ))

    hypotheses.append(Hypothesis(
        "unknown_insufficient_evidence", INSUFFICIENT_EVIDENCE,
        (), ("Root cause requires additional physical inspection evidence not present in canonical data",),
    ))
    return tuple(hypotheses)


def _overall_confidence(hypotheses: tuple[Hypothesis, ...]) -> str:
    ranked = {HIGH: 3, MEDIUM: 2, LOW: 1, INSUFFICIENT_EVIDENCE: 0}
    real = [h for h in hypotheses if h.cause != "unknown_insufficient_evidence"]
    if not real:
        return INSUFFICIENT_EVIDENCE
    return max((h.confidence for h in real), key=lambda c: ranked[c])


def _recommended_checks(
    *, has_leak_evidence: bool, temperature_evidence: dict[str, Any], vibration_evidence: dict[str, Any],
    seal_evidence: dict[str, Any], stock: tuple[StockReadinessRow, ...],
) -> tuple[str, ...]:
    if not has_leak_evidence:
        return ()
    checks = ["Verify actual leak source/location at the equipment", "Verify leak severity"]
    if temperature_evidence.get("status") == "FACT":
        checks.append("Inspect available temperature evidence and flush/cooling condition if applicable")
    else:
        checks.append("Record temperature readings at next inspection (currently DATA_GAP)")
    if vibration_evidence.get("status") == "FACT":
        checks.append("Inspect available vibration evidence")
    else:
        checks.append("Record vibration readings at next inspection (currently DATA_GAP)")
    checks.append("Verify current operating condition")
    if seal_evidence.get("confirmed_installed_seal") == DATA_GAP:
        checks.append("Confirm installed seal identity (currently unconfirmed)")
    checks.append("Review previous PM/CM records for this equipment")
    if any(row.state in (STOCK_ZERO, STOCK_NO_RECORD, STOCK_NO_COMPATIBLE_SEAL) for row in stock):
        checks.append("Prepare/verify compatible spare seal availability in case intervention is required")
    return tuple(checks)


# -- Public entry point ---------------------------------------------------------


def diagnose(
    tag: str,
    *,
    ltsa_knowledge_service,
    equipment_timeline_service=None,
    today: date | None = None,
) -> SealLeakDiagnosis:
    today = today or date.today()
    knowledge = ltsa_knowledge_service.build(tag)

    readings = list(knowledge.condition_monitoring_readings or [])
    leak_evidence, current_leak, historical_leak_count = _collect_leak_evidence(readings, today=today)
    has_leak_evidence = current_leak or historical_leak_count > 0

    latest_reading = readings[0] if readings else None
    previous_reading = readings[1] if len(readings) > 1 else None
    temperature_evidence = _collect_parameter_evidence(latest_reading, previous_reading, "temp")
    vibration_evidence = _collect_parameter_evidence(latest_reading, previous_reading, "vibration")
    operating_evidence = _collect_operating_evidence(latest_reading, knowledge.pump)

    maintenance_evidence = {
        "pm_count": len(knowledge.pm_history),
        "cm_count": len(knowledge.cm_history),
        "breakdown_count": len(knowledge.breakdown_history),
        "seal_failure_cm": any(r.get("failure_category") == "SEAL_FAILURE" for r in knowledge.cm_history),
    }

    installed_seal = None
    if equipment_timeline_service is not None:
        installed_seal = equipment_timeline_service.build_current_seal(tag)
    seal_evidence = _collect_seal_evidence(list(knowledge.seal), installed_seal)
    stock = _classify_stock(list(knowledge.seal), list(knowledge.inventory))

    missing_evidence = []
    if temperature_evidence.get("status") == DATA_GAP:
        missing_evidence.append("temperature")
    if vibration_evidence.get("status") == DATA_GAP:
        missing_evidence.append("vibration")
    if operating_evidence.get("status") == DATA_GAP:
        missing_evidence.append("operating_state")
    if seal_evidence.get("confirmed_installed_seal") == DATA_GAP:
        missing_evidence.append("confirmed_installed_seal")

    if not has_leak_evidence:
        return SealLeakDiagnosis(
            equipment=tag, diagnostic_status=STATUS_NO_LEAK,
            leak_evidence=leak_evidence, temperature_evidence=temperature_evidence,
            vibration_evidence=vibration_evidence, operating_evidence=operating_evidence,
            maintenance_evidence=maintenance_evidence, seal_evidence=seal_evidence,
            inventory_evidence=stock, hypotheses=(), recommended_checks=(),
            missing_evidence=tuple(missing_evidence), confidence=INSUFFICIENT_EVIDENCE,
            conclusion=CONCLUSION_NO_LEAK_EVIDENCE,
        )

    leak_findings_text = [r.get("finding") for r in readings if _is_leak_flagged(r)]
    latest_leak_date = _parse_date((leak_evidence.get("latest_leak_finding") or {}).get("reading_date"))
    hypotheses = _build_hypotheses(
        has_leak_evidence=has_leak_evidence, current_leak=current_leak,
        historical_leak_count=historical_leak_count, breakdown_count=maintenance_evidence["breakdown_count"],
        seal_failure_cm=maintenance_evidence["seal_failure_cm"], temperature_evidence=temperature_evidence,
        vibration_evidence=vibration_evidence, leak_findings_text=leak_findings_text,
        seal_evidence=seal_evidence, latest_leak_reading_date=latest_leak_date,
    )
    confidence = _overall_confidence(hypotheses)
    checks = _recommended_checks(
        has_leak_evidence=has_leak_evidence, temperature_evidence=temperature_evidence,
        vibration_evidence=vibration_evidence, seal_evidence=seal_evidence, stock=stock,
    )
    diagnostic_status = STATUS_LEAK_CURRENT if current_leak else STATUS_LEAK_HISTORICAL
    conclusion = CONCLUSION_PROBABLE_CAUSE if confidence != INSUFFICIENT_EVIDENCE else CONCLUSION_INSUFFICIENT_EVIDENCE

    return SealLeakDiagnosis(
        equipment=tag, diagnostic_status=diagnostic_status,
        leak_evidence=leak_evidence, temperature_evidence=temperature_evidence,
        vibration_evidence=vibration_evidence, operating_evidence=operating_evidence,
        maintenance_evidence=maintenance_evidence, seal_evidence=seal_evidence,
        inventory_evidence=stock, hypotheses=hypotheses, recommended_checks=checks,
        missing_evidence=tuple(missing_evidence), confidence=confidence, conclusion=conclusion,
    )


class SealLeakDiagnosticService:
    def __init__(self, *, ltsa_knowledge_service, equipment_timeline_service=None):
        self._ltsa_knowledge_service = ltsa_knowledge_service
        self._equipment_timeline_service = equipment_timeline_service

    def diagnose(self, tag: str) -> SealLeakDiagnosis:
        return diagnose(
            tag,
            ltsa_knowledge_service=self._ltsa_knowledge_service,
            equipment_timeline_service=self._equipment_timeline_service,
        )


__all__ = [
    "SealLeakDiagnosis", "Hypothesis", "StockReadinessRow", "SealLeakDiagnosticService", "diagnose",
    "HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE", "DATA_GAP",
    "STATUS_LEAK_CURRENT", "STATUS_LEAK_HISTORICAL", "STATUS_NO_LEAK",
    "STOCK_AVAILABLE", "STOCK_ZERO", "STOCK_NO_RECORD", "STOCK_NO_COMPATIBLE_SEAL",
    "CONCLUSION_PROBABLE_CAUSE", "CONCLUSION_INSUFFICIENT_EVIDENCE", "CONCLUSION_NO_LEAK_EVIDENCE",
]

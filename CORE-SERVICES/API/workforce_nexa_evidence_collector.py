"""Read-only LTSA operational evidence collector for NEXA Report Analyst.

Collects bounded, normalized evidence snapshots across canonical LTSA operational domains:
- asset_registry / ltsa_pumps
- condition_monitoring_reading (strictly reading_date; Condition Monitoring, NOT Corrective Maintenance)
- pm_occurrence (strictly occurrence_date) & pm_schedule
- installation_report (strictly report_date)
- mechanical_seal_stock_pool & seal_registry
- historical_seal_service_activity (strictly event_date)

Zero write paths. Zero database mutations. Deterministic JSON serialization and SHA-256 hashing.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
import sys

_API_DIR = Path(__file__).resolve().parent
_INGESTION_DIR = _API_DIR.parent.parent / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

try:
    from ltsa_pump_inventory_db_upsert import _json_query, _sql
except ImportError:
    def _sql(v: Any) -> str:
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        if isinstance(v, (int, float)):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"

    def _json_query(sql: str, runner: Any) -> list[dict[str, Any]]:
        raw = runner.query_scalar(f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;")
        return json.loads(raw or "[]")

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

AVAILABLE_SOURCE_DOMAINS = (
    "asset_registry",
    "condition_monitoring_reading",
    "pm_occurrence",
    "installation_report",
    "mechanical_seal",
    "historical_seal_service_activity",
)
UNAVAILABLE_SOURCE_DOMAINS: tuple[str, ...] = ()

DEFAULT_MAX_DOMAIN_ITEMS = 100


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_iso_date(value: str, field_name: str) -> date:
    if not isinstance(value, str) or not DATE_PATTERN.match(value.strip()):
        raise ValueError(f"{field_name} must be a valid date in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as err:
        raise ValueError(f"{field_name} is not a valid calendar date: {value}") from err


def sanitize_raw_string(text: str) -> str:
    """Neutralize potential prompt injection delimiters in raw data strings."""
    if not isinstance(text, str):
        return text
    return (
        text.replace("<ltsa_evidence_data>", "[evidence_data]")
        .replace("</ltsa_evidence_data>", "[/evidence_data]")
        .replace("<system>", "[system]")
        .replace("</system>", "[/system]")
    )


def sanitize_data(obj: Any) -> Any:
    if isinstance(obj, str):
        return sanitize_raw_string(obj)
    if isinstance(obj, list):
        return [sanitize_data(item) for item in obj]
    if isinstance(obj, dict):
        return {k: sanitize_data(v) for k, v in obj.items()}
    return obj


def canonical_json(data: Any) -> str:
    """Stable, deterministic JSON serialization with sorted keys."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def compute_evidence_sha256(canonical_payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of the normalized evidence data."""
    encoded = canonical_json(canonical_payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class LTSAEvidenceCollector:
    """Read-only collector that queries approved LTSA operational data and builds bounded snapshots."""

    def __init__(
        self,
        runner: Any = None,
        *,
        data_provider: Callable[[str, str, str, str | None], list[dict[str, Any]]] | None = None,
        max_domain_items: int = DEFAULT_MAX_DOMAIN_ITEMS,
    ) -> None:
        self.runner = runner
        self.data_provider = data_provider
        self.max_domain_items = max_domain_items

    def _query_domain(
        self,
        domain: str,
        start_date: str,
        end_date: str,
        area: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.data_provider is not None:
            return self.data_provider(domain, start_date, end_date, area)

        if self.runner is None:
            return []

        area_filter = f"AND pump.area = {_sql(area)}" if area else ""

        if domain == "asset_registry":
            pump_area_filter = f"WHERE area = {_sql(area)}" if area else ""
            sql = (
                "SELECT tag_number, name, area, service, manufacturer, model, criticality, status "
                f"FROM public.ltsa_pumps {pump_area_filter} ORDER BY tag_number ASC"
            )
            return _json_query(sql, self.runner)

        if domain == "condition_monitoring_reading":
            # Condition Monitoring semantics: reading_date controls period, NOT legacy cm_report.
            sql = (
                "SELECT r.condition_monitoring_reading_code, r.condition_monitoring_schedule_code, "
                "r.asset_code, r.asset_type, r.reading_date::text AS reading_date, r.workflow_status, "
                "r.provenance, r.finding, r.pump_operating_state, r.suction_pressure, r.discharge_pressure, "
                "r.vertical_vibration_de, r.vertical_vibration_nde, r.horizontal_vibration_de, "
                "r.horizontal_vibration_nde, r.axial_vibration_de, r.axial_vibration_nde, "
                "r.bearing_temp_de, r.bearing_temp_nde, r.motor_current, pump.area, pump.name AS pump_name "
                "FROM public.condition_monitoring_reading r "
                "LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = r.asset_code "
                f"WHERE r.deleted_at IS NULL AND r.reading_date >= {_sql(start_date)} "
                f"AND r.reading_date <= {_sql(end_date)} {area_filter} "
                "ORDER BY r.reading_date ASC, r.condition_monitoring_reading_code ASC"
            )
            return _json_query(sql, self.runner)

        if domain == "pm_occurrence":
            # Canonical PM occurrence semantics: occurrence_date controls period.
            sql = (
                "SELECT r.pm_occurrence_code, r.pm_schedule_code, r.asset_code, r.asset_type, "
                "r.occurrence_date::text AS occurrence_date, r.status, r.workflow_status, r.finding, "
                "r.preliminary_recommendation, r.remarks, r.provenance, pump.area, pump.name AS pump_name "
                "FROM public.pm_occurrence r "
                "LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = r.asset_code "
                f"WHERE r.deleted_at IS NULL AND r.occurrence_date >= {_sql(start_date)} "
                f"AND r.occurrence_date <= {_sql(end_date)} {area_filter} "
                "ORDER BY r.occurrence_date ASC, r.pm_occurrence_code ASC"
            )
            return _json_query(sql, self.runner)

        if domain == "installation_report":
            # Canonical installation reports: report_date controls period.
            inst_area_filter = f"AND (pump.area = {_sql(area)} OR pump.area IS NULL)" if area else ""
            sql = (
                "SELECT i.installation_code, i.report_no, i.report_date::text AS report_date, "
                "i.plant_equip_no, i.pump_tag_number, i.seal_code, i.seal_type, i.seal_manufacture, "
                "i.seal_size, i.material_code, pump.area "
                "FROM public.installation_report i "
                "LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = i.pump_tag_number "
                f"WHERE i.report_date >= {_sql(start_date)} AND i.report_date <= {_sql(end_date)} "
                f"{inst_area_filter} ORDER BY i.report_date ASC, i.installation_code ASC"
            )
            return _json_query(sql, self.runner)

        if domain == "mechanical_seal":
            sql = (
                "SELECT stock_pool_id, seal_type, size_range, count_available, count_in_service, "
                "verification_status FROM public.mechanical_seal_stock_pool ORDER BY stock_pool_id ASC"
            )
            return _json_query(sql, self.runner)

        if domain == "historical_seal_service_activity":
            # Historical activity: event_date controls period.
            hist_area_filter = f"AND (h.ltsa_area = {_sql(area)} OR h.ltsa_area IS NULL)" if area else ""
            sql = (
                "SELECT h.activity_id, h.pump_tag_number, h.event_type, h.event_date::text AS event_date, "
                "h.failure_attribution, h.seal_type, h.seal_size, h.status, h.remarks, h.ltsa_area "
                "FROM public.historical_seal_service_activity h "
                f"WHERE h.event_date >= {_sql(start_date)} AND h.event_date <= {_sql(end_date)} "
                f"{hist_area_filter} ORDER BY h.event_date ASC, h.activity_id ASC"
            )
            return _json_query(sql, self.runner)

        return []

    def collect_evidence(
        self,
        *,
        start_date: str,
        end_date: str,
        area: str | None = None,
        mission_id: str | None = None,
    ) -> dict[str, Any]:
        """Collect bounded, sanitized, deterministic evidence snapshot."""
        d_start = validate_iso_date(start_date, "start_date")
        d_end = validate_iso_date(end_date, "end_date")
        if d_start > d_end:
            raise ValueError("start_date cannot be after end_date")

        norm_start = d_start.isoformat()
        norm_end = d_end.isoformat()
        norm_area = area.strip() if (isinstance(area, str) and area.strip()) else None

        raw_domains: dict[str, list[dict[str, Any]]] = {}
        original_counts: dict[str, int] = {}
        included_counts: dict[str, int] = {}
        truncation_reasons: list[str] = []
        is_truncated = False

        for domain in AVAILABLE_SOURCE_DOMAINS:
            items = self._query_domain(domain, norm_start, norm_end, norm_area)
            sanitized = sanitize_data(items)
            original_counts[domain] = len(sanitized)
            if len(sanitized) > self.max_domain_items:
                is_truncated = True
                bounded = sanitized[: self.max_domain_items]
                truncation_reasons.append(
                    f"Domain '{domain}' truncated from {len(sanitized)} to {self.max_domain_items} items"
                )
            else:
                bounded = sanitized
            included_counts[domain] = len(bounded)
            raw_domains[domain] = bounded

        # Deterministic payload used for hashing (excludes volatile timestamp)
        hash_payload = {
            "period_start": norm_start,
            "period_end": norm_end,
            "area_filter": norm_area,
            "source_domains": list(AVAILABLE_SOURCE_DOMAINS),
            "source_row_counts": included_counts,
            "evidence_truncated": is_truncated,
            "original_counts": original_counts,
            "included_counts": included_counts,
            "domains": raw_domains,
        }

        sha256 = compute_evidence_sha256(hash_payload)

        return {
            "mission_id": mission_id,
            "period_start": norm_start,
            "period_end": norm_end,
            "area_filter": norm_area,
            "generated_at": utc_now(),
            "source_domains": list(AVAILABLE_SOURCE_DOMAINS),
            "source_row_counts": included_counts,
            "evidence_truncated": is_truncated,
            "truncation_reason": "; ".join(truncation_reasons) if truncation_reasons else None,
            "original_counts": original_counts,
            "included_counts": included_counts,
            "evidence_sha256": sha256,
            "domains": raw_domains,
        }

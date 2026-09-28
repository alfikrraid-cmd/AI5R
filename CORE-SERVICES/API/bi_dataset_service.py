"""LTSA_POWER_BI_R1B -- governed, read-only BI datasets (contract ltsa-bi/1.0.0).

Power BI imports these tables; it never recreates LTSA business logic. Every
rule here is delegated to the existing canonical contracts:

  * area            -> pump_contract_area.resolve_contract_area,
                       pump_area_scope.normalize_area_token / resolve_area_ma /
                       format_area_display (divergences exposed, not reconciled)
  * CM leak state   -> cm_condition_evaluator.canonical_leak_state /
                       is_active_leak / current_leak_condition
  * installations   -> historical_installation_evidence.combined_installation_evidence
                       + current_installation_contract.valid_installation_events
  * MTBF intervals  -> installation_interval_contract.installation_based_mtbf
  * current install -> current_installation_contract.resolve_current_installation
                       (installation_report only -- historical evidence never
                       becomes Current Installation; service age is not MTBF)

Reads are bulk: one query per source, grouped in memory, so no table ever
issues one query per pump. Tables are never truncated: a table larger than
max_rows raises BiTableLimitExceeded instead of returning a partial set.

Each call builds an independent snapshot (its own generated_at_utc and plant
as_of_date); separate HTTP calls are NOT transactionally consistent with each
other, so counts may differ between a table and /metadata when data is
written in between -- the reconciliation contract detects that.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .cm_condition_evaluator import canonical_leak_state, current_leak_condition, is_active_leak
from .current_installation_contract import (
    PLANT_TIMEZONE_NAME,
    STATUS_INSTALLED,
    parse_installation_moment,
    plant_now,
    resolve_current_installation,
    valid_installation_events,
)
from .historical_installation_evidence import (
    ORIGIN_HISTORICAL_SERVICE_ACTIVITY,
    combined_installation_evidence,
)
from .installation_interval_contract import POSITION_PUMP_LEVEL, installation_based_mtbf
from .pump_area_scope import format_area_display, normalize_area_token, resolve_area_ma
from .pump_contract_area import UNCLASSIFIED, resolve_contract_area

logger = logging.getLogger(__name__)

CONTRACT_VERSION = "ltsa-bi/1.0.0"
MAX_ROWS = 50_000
NOT_RECORDED_AREA_KEY = "__NOT_RECORDED__"
MTTR_STATUS = "DATA NOT AVAILABLE"
LEAK_TRUE, LEAK_FALSE, LEAK_NOT_RECORDED = "TRUE", "FALSE", "NOT_RECORDED"


class BiError(Exception):
    status_code = 500
    error_code = "BI_INTERNAL_ERROR"


class BiTableLimitExceeded(BiError):
    status_code = 413
    error_code = "BI_TABLE_LIMIT_EXCEEDED"


class BiSourceUnavailable(BiError):
    status_code = 503
    error_code = "BI_SOURCE_UNAVAILABLE"


def leak_tristate(value: Any) -> str:
    """Lossless tri-state: only the literal booleans are recorded values."""
    if value is True:
        return LEAK_TRUE
    if value is False:
        return LEAK_FALSE
    return LEAK_NOT_RECORDED


def _date_part(value: Any) -> str | None:
    """YYYY-MM-DD of a stored DATE / naive plant-local TIMESTAMP value."""
    if value is None:
        return None
    text = str(value)
    return text[:10] if len(text) >= 10 else None


def _local_date(installation_date: str | None) -> str | None:
    """Plant-local date of a canonical installation date (DATE_ONLY or TIMESTAMP)."""
    if not installation_date:
        return None
    parsed = parse_installation_moment(installation_date)
    return parsed[0].isoformat() if parsed else None


def _group(rows: Iterable[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get(key):
            grouped[row[key]].append(row)
    return grouped


def area_fields(raw_area: Any) -> dict[str, Any]:
    """The canonical area classification of one raw asset_registry.area value."""
    recorded = raw_area if isinstance(raw_area, str) and raw_area.strip() else None
    return {
        "raw_area_key": recorded if recorded is not None else NOT_RECORDED_AREA_KEY,
        "raw_area": recorded,
        "contract_area": resolve_contract_area(recorded),
        "maintenance_area": resolve_area_ma(recorded) or UNCLASSIFIED,
    }


@dataclass(frozen=True)
class BiSnapshot:
    generated_at_utc: str
    as_of_date: str
    now: datetime


@dataclass(frozen=True)
class _PumpModel:
    installations: list[dict[str, Any]]
    intervals: list[dict[str, Any]]
    pump_current: list[dict[str, Any]]
    excluded_same_day: int
    non_comparable_transitions: int


class BiDatasetService:
    def __init__(
        self,
        *,
        asset_repository: Any,
        cm_repository: Any,
        pm_repository: Any,
        installation_report_repository: Any,
        historical_repository: Any,
        seal_lifecycle_repository: Any,
        clock: Callable[[], datetime] | None = None,
        max_rows: int = MAX_ROWS,
    ) -> None:
        self._assets = asset_repository
        self._cm = cm_repository
        self._pm = pm_repository
        self._installation_reports = installation_report_repository
        self._historical = historical_repository
        self._lifecycle = seal_lifecycle_repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.max_rows = max_rows

    # -- snapshot / envelope -------------------------------------------------------------------------

    def snapshot(self) -> BiSnapshot:
        moment = self._clock()
        plant = plant_now(moment)
        generated = moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        return BiSnapshot(generated_at_utc=generated, as_of_date=plant.date().isoformat(), now=plant)

    def _envelope(self, table: str, rows: list[dict[str, Any]], order_by: str, snap: BiSnapshot) -> dict[str, Any]:
        if len(rows) > self.max_rows:
            # Never a partial table: the caller gets an error, not the first max_rows rows.
            raise BiTableLimitExceeded(f"{table} has {len(rows)} rows, above the {self.max_rows} row limit")
        return {
            "success": True,
            "contract_version": CONTRACT_VERSION,
            "table": table,
            "generated_at_utc": snap.generated_at_utc,
            "as_of_date": snap.as_of_date,
            "plant_timezone": PLANT_TIMEZONE_NAME,
            "row_count": len(rows),
            "max_rows": self.max_rows,
            "order_by": order_by,
            "data": rows,
        }

    @staticmethod
    def _read(label: str, reader: Callable[[], Any]) -> list[dict[str, Any]]:
        try:
            return list(reader() or [])
        except Exception as error:  # noqa: BLE001 -- any source failure is a 503, never partial data
            logger.exception("BI source read failed: %s", label)
            raise BiSourceUnavailable(f"source unavailable: {label}") from error

    # -- source reads (one bulk query each) --------------------------------------------------------------------

    def _asset_rows(self) -> list[dict[str, Any]]:
        rows = self._read("assets", self._assets.list_assets_with_pump_enrichment)
        codes = [row.get("asset_code") for row in rows]
        if len(codes) != len(set(codes)):
            # ltsa_pumps.tag_number has no UNIQUE constraint; a duplicate would
            # double an asset -- fail loudly rather than pick one silently.
            raise BiSourceUnavailable("assets: duplicate asset_code in asset/pump enrichment join")
        return rows

    # -- tables ------------------------------------------------------------------------------------------------

    def assets_rows(self) -> list[dict[str, Any]]:
        out = []
        for row in self._asset_rows():
            area = area_fields(row.get("raw_area"))
            out.append(
                {
                    "asset_code": row.get("asset_code"),
                    "asset_name": row.get("asset_name"),
                    "asset_type": row.get("asset_type"),
                    "is_pump": row.get("asset_type") == "PUMP",
                    "asset_status": row.get("asset_status"),
                    "raw_area_key": area["raw_area_key"],
                    "raw_area": area["raw_area"],
                    "contract_area": area["contract_area"],
                    "maintenance_area": area["maintenance_area"],
                    "pump_enrichment_present": bool(row.get("pump_enrichment_present")),
                    "pump_type": row.get("pump_type"),
                    "api_plan": row.get("api_plan"),
                    "configured_seal_type": row.get("configured_seal_type"),
                    "criticality": row.get("criticality"),
                    "ltsa_location": row.get("ltsa_location"),
                }
            )
        return sorted(out, key=lambda r: r["asset_code"])

    def areas_rows(self) -> list[dict[str, Any]]:
        counts: dict[str, int] = defaultdict(int)
        raw_by_key: dict[str, Any] = {}
        for row in self._asset_rows():
            fields = area_fields(row.get("raw_area"))
            counts[fields["raw_area_key"]] += 1
            raw_by_key[fields["raw_area_key"]] = fields["raw_area"]
        out = []
        for key in sorted(counts):
            raw = raw_by_key[key]
            out.append(
                {
                    **area_fields(raw),
                    "area_code": normalize_area_token(raw),
                    "area_display": format_area_display(raw),
                    "asset_count": counts[key],
                }
            )
        return out

    def cm_rows(self) -> list[dict[str, Any]]:
        out = []
        for row in self._read("condition_monitoring_reading", self._cm.list_all_live):
            de, nde = row.get("mechanical_seal_leak_de"), row.get("mechanical_seal_leak_nde")
            state = canonical_leak_state(de, nde)
            out.append(
                {
                    "reading_code": row.get("condition_monitoring_reading_code"),
                    "asset_code": row.get("asset_code"),
                    "reading_date": _date_part(row.get("reading_date")),
                    "reading_timestamp_local": row.get("reading_date"),
                    "workflow_status": row.get("workflow_status"),
                    "pump_operating_state": row.get("pump_operating_state"),
                    "provenance": row.get("provenance"),
                    "source_reference": row.get("source_reference"),
                    "leak_de": leak_tristate(de),
                    "leak_nde": leak_tristate(nde),
                    "canonical_leak_state": state,
                    "leak_active": is_active_leak(state),
                    "finding": row.get("finding"),
                    "technical_recommendation": row.get("technical_recommendation"),
                    "api_plan_snapshot": row.get("api_plan_snapshot"),
                }
            )
        return sorted(out, key=lambda r: r["reading_code"] or "")

    def pm_rows(self) -> list[dict[str, Any]]:
        out = [
            {
                "pm_occurrence_code": row.get("pm_occurrence_code"),
                "asset_code": row.get("asset_code"),
                "occurrence_date": _date_part(row.get("occurrence_date")),
                "occurrence_timestamp_local": row.get("occurrence_date"),
                "status": row.get("status"),
                "workflow_status": row.get("workflow_status"),
                "provenance": row.get("provenance"),
                "source_reference": row.get("source_reference"),
                "finding": row.get("finding"),
            }
            for row in self._read("pm_occurrence", self._pm.list_all_live)
        ]
        return sorted(out, key=lambda r: r["pm_occurrence_code"] or "")

    def _pump_model(self, snap: BiSnapshot, *, include_current_condition: bool = True) -> _PumpModel:
        assets = self._asset_rows()
        pumps = sorted(row["asset_code"] for row in assets if row.get("asset_type") == "PUMP")
        reports = _group(self._read("installation_report", self._installation_reports.list_for_registered_pumps), "pump_tag_number")
        historical_rows = self._read("historical_seal_service_activity", self._historical.list_governed_installation_events)
        historical = _group(historical_rows, "pump_tag_number")
        historical_by_id = {row["historical_event_id"]: row for row in historical_rows if row.get("historical_event_id")}
        removals = _group(self._read("seal_lifecycle_event", self._lifecycle.list_all_pump_events), "pump_tag_number")
        readings = _group(self._read("condition_monitoring_reading", self._cm.list_all_live), "asset_code") if include_current_condition else {}

        installations: list[dict[str, Any]] = []
        intervals: list[dict[str, Any]] = []
        pump_current: list[dict[str, Any]] = []
        excluded_same_day = non_comparable = 0

        for tag in pumps:
            pump_reports = reports.get(tag, [])
            combined = combined_installation_evidence(pump_reports, historical.get(tag, []))
            origin_by_code = {record["installation_code"]: record.get("evidence_origin") for record in combined}

            for event in reversed(valid_installation_events(combined, tag)):  # date ASC, code ASC
                origin = origin_by_code.get(event.installation_code)
                source = historical_by_id.get(event.installation_code) if origin == ORIGIN_HISTORICAL_SERVICE_ACTIVITY else None
                installations.append(
                    {
                        "event_id": event.installation_code,
                        "event_source": origin,
                        "asset_code": tag,
                        "position": event.installation_position or POSITION_PUMP_LEVEL,
                        "event_date": _local_date(event.installation_date),
                        "date_precision": event.time_precision,
                        "event_type": (source or {}).get("event_type") or "INSTALLATION",
                        "seal_type": event.installed_seal_type,
                        "seal_size": event.installed_seal_size,
                        "seal_code": event.seal_code,
                        "evidence_grade": (source or {}).get("evidence_grade"),
                        "date_correction_status": (source or {}).get("date_correction_status"),
                        "source_reference": (source or {}).get("source_reference") if source else event.report_no,
                        "source_document": event.source_document,
                    }
                )

            mtbf = installation_based_mtbf(combined, tag)
            excluded_same_day += len(mtbf.excluded_intervals)
            non_comparable += len(mtbf.non_comparable_transitions)
            for interval in mtbf.intervals:
                intervals.append(
                    {
                        "interval_id": f"{tag}|{interval.position}|{interval.previous_installation_code}|{interval.next_installation_code}",
                        "asset_code": tag,
                        "position": interval.position,
                        "start_event_id": interval.previous_installation_code,
                        "end_event_id": interval.next_installation_code,
                        "start_date": _local_date(interval.previous_installation_date),
                        "end_date": _local_date(interval.next_installation_date),
                        "mtbf_days": interval.mtbf_days,
                        "mtbf_hours": interval.mtbf_hours,
                        "calendar_basis": interval.time_basis,
                        "precision": interval.precision,
                        "seal_identity_transition": interval.seal_identity_status,
                        "start_seal_type": interval.previous_seal_type,
                        "start_seal_size": interval.previous_seal_size,
                        "end_seal_type": interval.next_seal_type,
                        "end_seal_size": interval.next_seal_size,
                    }
                )

            if not include_current_condition:
                continue
            # Current Installation: installation_report ONLY, exactly as the application resolves it.
            current = resolve_current_installation(
                pump_reports, tag, removal_events=removals.get(tag, []), now=snap.now
            ).current
            pump_readings = readings.get(tag, [])
            condition = current_leak_condition(pump_readings)
            selected = next(
                (r for r in pump_readings if r.get("condition_monitoring_reading_code") == condition["reading_code"]),
                None,
            )
            installed = current.installation_status == STATUS_INSTALLED
            pump_current.append(
                {
                    "asset_code": tag,
                    "as_of_timestamp_utc": snap.generated_at_utc,
                    "as_of_date": snap.as_of_date,
                    "current_cm_reading_code": condition["reading_code"],
                    "current_cm_reading_date": _date_part(condition["reading_date"]),
                    "current_cm_workflow_status": condition["workflow_status"],
                    "current_pump_operating_state": (selected or {}).get("pump_operating_state"),
                    "current_leak_state": condition["state"],
                    "current_leak_active": bool(condition["active"]),
                    "current_installation_status": current.installation_status,
                    "current_installation_code": current.source_installation_code,
                    "current_installation_date": _local_date(current.installation_date),
                    "current_installation_position": (current.installation_position or POSITION_PUMP_LEVEL) if installed else None,
                    "current_installed_seal_type": current.installed_seal_type,
                    "current_installed_seal_size": current.installed_seal_size,
                    "current_service_age_days": current.time_since_installation_days,
                    "current_service_age_hours": current.time_since_installation_hours,
                    "current_service_age_basis": current.time_basis,
                    "current_service_age_precision": current.time_precision,
                    "pump_mtbf_completed_interval_count": mtbf.completed_interval_count,
                    "pump_mtbf_days_mean": mtbf.installation_based_mtbf_days,
                    "pump_mtbf_hours_mean": mtbf.installation_based_mtbf_hours,
                    "pump_mtbf_latest_interval_days": mtbf.intervals[-1].mtbf_days if mtbf.intervals else None,
                }
            )

        installations.sort(key=lambda r: (r["asset_code"], r["event_date"] or "", r["event_id"]))
        intervals.sort(key=lambda r: (r["asset_code"], r["position"], r["start_date"] or "", r["start_event_id"]))
        return _PumpModel(installations, intervals, pump_current, excluded_same_day, non_comparable)

    # -- endpoint payloads ---------------------------------------------------------------------------------------

    def assets(self) -> dict[str, Any]:
        snap = self.snapshot()
        return self._envelope("assets", self.assets_rows(), "asset_code", snap)

    def areas(self) -> dict[str, Any]:
        snap = self.snapshot()
        return self._envelope("areas", self.areas_rows(), "raw_area_key", snap)

    def cm(self) -> dict[str, Any]:
        snap = self.snapshot()
        return self._envelope("cm", self.cm_rows(), "reading_code", snap)

    def pm(self) -> dict[str, Any]:
        snap = self.snapshot()
        return self._envelope("pm", self.pm_rows(), "pm_occurrence_code", snap)

    def installations(self) -> dict[str, Any]:
        snap = self.snapshot()
        model = self._pump_model(snap, include_current_condition=False)
        return self._envelope("installations", model.installations, "asset_code,event_date,event_id", snap)

    def mtbf_intervals(self) -> dict[str, Any]:
        snap = self.snapshot()
        model = self._pump_model(snap, include_current_condition=False)
        return self._envelope("mtbf-intervals", model.intervals, "asset_code,position,start_date,start_event_id", snap)

    def pump_current(self) -> dict[str, Any]:
        snap = self.snapshot()
        model = self._pump_model(snap)
        return self._envelope("pump-current", model.pump_current, "asset_code", snap)

    def metadata(self) -> dict[str, Any]:
        snap = self.snapshot()
        assets = self.assets_rows()
        cm = self.cm_rows()
        pm = self.pm_rows()
        model = self._pump_model(snap)
        pump_population = len(model.pump_current)
        covered = sum(1 for row in model.pump_current if row["pump_mtbf_completed_interval_count"] >= 1)
        fact_dates = [
            d
            for d in (
                *(r["reading_date"] for r in cm),
                *(r["occurrence_date"] for r in pm),
                *(r["event_date"] for r in model.installations),
                *(r["end_date"] for r in model.intervals),
            )
            if d
        ]
        sizes = {
            "assets": len(assets),
            "cm": len(cm),
            "pm": len(pm),
            "installations": len(model.installations),
            "mtbf-intervals": len(model.intervals),
            "pump-current": pump_population,
        }
        return {
            "success": True,
            "contract_version": CONTRACT_VERSION,
            "table": "metadata",
            "generated_at_utc": snap.generated_at_utc,
            "as_of_date": snap.as_of_date,
            "plant_timezone": PLANT_TIMEZONE_NAME,
            "asset_count": len(assets),
            "pump_count": pump_population,
            "cm_count": len(cm),
            "pm_count": len(pm),
            "installation_event_count": len(model.installations),
            "installation_report_count": sum(1 for r in model.installations if r["event_source"] != ORIGIN_HISTORICAL_SERVICE_ACTIVITY),
            "historical_installation_count": sum(1 for r in model.installations if r["event_source"] == ORIGIN_HISTORICAL_SERVICE_ACTIVITY),
            "mtbf_interval_count": len(model.intervals),
            "mtbf_pump_coverage_count": covered,
            "mtbf_pump_population": pump_population,
            "mtbf_coverage_pct": round(100 * covered / pump_population, 2) if pump_population else None,
            "mtbf_excluded_same_day_count": model.excluded_same_day,
            "mtbf_non_comparable_transition_count": model.non_comparable_transitions,
            "min_fact_date": min(fact_dates) if fact_dates else None,
            "max_fact_date": max(fact_dates) if fact_dates else None,
            "max_rows": self.max_rows,
            "largest_table_rows": max(sizes.values()) if sizes else 0,
            "mttr_available": False,
            "mttr_status": MTTR_STATUS,
            "snapshot_consistency": "PER_REQUEST",
        }


__all__ = [
    "BiDatasetService",
    "BiError",
    "BiSnapshot",
    "BiSourceUnavailable",
    "BiTableLimitExceeded",
    "CONTRACT_VERSION",
    "LEAK_FALSE",
    "LEAK_NOT_RECORDED",
    "LEAK_TRUE",
    "MAX_ROWS",
    "MTTR_STATUS",
    "NOT_RECORDED_AREA_KEY",
    "area_fields",
    "leak_tristate",
]

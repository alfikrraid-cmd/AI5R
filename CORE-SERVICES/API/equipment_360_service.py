"""MWO-LTSA-EQUIPMENT-360-001 -- canonical Equipment 360 read aggregator.

Exists to PROVE (not just assert) that every equipment-scoped READ intent in
copilot_ask_service.py can be built from one shared set of canonical facts:
every field below is read through the exact same repository/service each
fixed handler in that module already uses (pm_occurrence_repository,
cm_report_repository, condition_monitoring_reading_repository,
equipment_timeline_service.build_current_seal, mechanical_seal_stock_
repository via maintenance_intelligence_service.flatten_stock_v1_fleet_rows).
No new SQL, no new gateway, no re-derivation of any fact -- this module adds
zero new data paths, only a shared read shape over the ones that already
exist.

Never fabricates: a category with no records is an empty tuple/None (a
truthful FACT), never a guess; a category the underlying call could not
reach is named in `data_gaps` instead of being silently rendered as "0"/
"none" (see the stock quantity_available=4/location=N/A example this MWO's
own mission text calls out -- "unavailable" and "confirmed empty" are never
the same state here).

Known, deliberately deferred limitation: compatible_seals/drawings are read
via ltsa_knowledge_service.build(tag), which still internally constructs its
own n8n gateways when not explicitly given one -- the SAME limitation
_handle_seal_compat/_handle_drawing_document/_handle_recommendation in
copilot_ask_service.py already carry. Fixing it requires modifying a shared,
multi-consumer service class and was scoped OUT of this MWO (see its Final
Report); this aggregator surfaces the same not-yet-canonical data those
three handlers do, not a different or additionally-fixed version of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import maintenance_intelligence_service as mis


@dataclass(frozen=True, slots=True)
class Equipment360:
    equipment_tag: str
    status: str | None
    area: str | None
    location: str | None
    pump_type: str | None
    pm_latest: dict[str, Any] | None
    pm_history: tuple[dict[str, Any], ...]
    cm_latest: dict[str, Any] | None
    cm_history: tuple[dict[str, Any], ...]
    cmon_latest: dict[str, Any] | None
    cmon_history: tuple[dict[str, Any], ...]
    current_seal: Any | None
    compatible_seals: tuple[dict[str, Any], ...]
    seal_stock: tuple[dict[str, Any], ...]
    drawings: tuple[dict[str, Any], ...]
    data_gaps: tuple[str, ...]


def get_equipment_360(
    tag: str,
    *,
    pump_gateway,
    pm_occurrence_repository,
    cm_report_repository,
    condition_monitoring_reading_repository,
    equipment_timeline_service,
    ltsa_knowledge_service,
    mechanical_seal_stock_repository,
) -> Equipment360:
    gaps: list[str] = []

    # Identity/status/area/location -- PumpGateway, used universally and
    # consistently across the whole system (auth scope resolution, tag
    # validation, _handle_pump_status) -- never a second, disconnected
    # identity source.
    status = area = location = pump_type = None
    try:
        response = pump_gateway.get_pump(tag)
        pump = response.get("data") if isinstance(response, dict) else None
        if response.get("success") and isinstance(pump, dict):
            status = pump.get("status")
            area = pump.get("area")
            location = pump.get("location")
            pump_type = pump.get("pump_type")
        else:
            gaps.append("pump_identity")
    except Exception:
        gaps.append("pump_identity")

    # PM -- pm_occurrence_repository (direct-DB), the same canonical
    # repository the WhatsApp PM WRITE flow persists through. Already
    # ORDER BY occurrence_date DESC NULLS LAST, created_at DESC -- records[0]
    # is the newest, no re-sorting here.
    pm_latest: dict[str, Any] | None = None
    pm_history: tuple[dict[str, Any], ...] = ()
    try:
        records = pm_occurrence_repository.list_by_asset(tag)
        if isinstance(records, list):
            pm_history = tuple(records)
            pm_latest = records[0] if records else None
        else:
            gaps.append("pm")
    except Exception:
        gaps.append("pm")

    # CM -- cm_report_repository (direct-DB), the same canonical repository
    # routers/cm_report.py's own dashboard endpoint already depends on.
    # Already ORDER BY COALESCE(failure_date, created_at) DESC -- filtering
    # by asset_code preserves that ordering.
    cm_latest: dict[str, Any] | None = None
    cm_history: tuple[dict[str, Any], ...] = ()
    try:
        response = cm_report_repository.list_cm_reports()
        if response.get("success"):
            records = [r for r in (response.get("data") or []) if r.get("asset_code") == tag]
            cm_history = tuple(records)
            cm_latest = records[0] if records else None
        else:
            gaps.append("cm")
    except Exception:
        gaps.append("cm")

    # CMON -- condition_monitoring_reading_repository (direct-DB), the same
    # canonical repository the WhatsApp/dashboard CMON WRITE flow persists
    # through. DRAFT status is surfaced truthfully via cmon_latest's own
    # workflow_status field, never silently promoted to confirmed.
    cmon_latest: dict[str, Any] | None = None
    cmon_history: tuple[dict[str, Any], ...] = ()
    try:
        records = condition_monitoring_reading_repository.list_by_asset(tag)
        if isinstance(records, list):
            cmon_history = tuple(records)
            cmon_latest = records[0] if records else None
        else:
            gaps.append("cmon")
    except Exception:
        gaps.append("cmon")

    # Current installed seal -- equipment_timeline_service.build_current_
    # seal(tag), the ONE identity-safe, evidence-required source (see
    # copilot_ask_service.py's own IDENTITY SAFETY header). None means "no
    # confirmed current-seal installation record", never "no seal" and
    # never filled in from a compatible-seal entry below.
    current_seal = None
    try:
        current_seal = equipment_timeline_service.build_current_seal(tag)
        if current_seal is None:
            gaps.append("current_seal")
    except Exception:
        gaps.append("current_seal")

    # Compatible seals / drawings -- ltsa_knowledge_service.build(tag).
    # KNOWN LIMITATION (see module docstring): still n8n-backed internally.
    # Compatibility evidence only -- never merged into/treated as current_
    # seal above.
    compatible_seals: tuple[dict[str, Any], ...] = ()
    drawings: tuple[dict[str, Any], ...] = ()
    try:
        knowledge = ltsa_knowledge_service.build(tag)
        compatible_seals = tuple(knowledge.seal or ())
        drawings = tuple(knowledge.drawings or ())
    except Exception:
        gaps.append("compatible_seals")
        gaps.append("drawings")

    # Seal stock -- mechanical_seal_stock_repository (Stock V1), the ONLY
    # stock authority Copilot reads from. flatten_stock_v1_fleet_rows reuses
    # Stock V1's own real (equipment_tag, pool) application mapping
    # unmodified -- never infers a pump's stock from a pool it has no real
    # application row for.
    seal_stock: tuple[dict[str, Any], ...] = ()
    try:
        response = mechanical_seal_stock_repository.list_pools(limit=200)
        if response.get("success"):
            rows = mis.flatten_stock_v1_fleet_rows(response.get("data") or [])
            seal_stock = tuple(row for row in rows if row["equipment_tag"] == tag)
        else:
            gaps.append("seal_stock")
    except Exception:
        gaps.append("seal_stock")

    return Equipment360(
        equipment_tag=tag,
        status=status,
        area=area,
        location=location,
        pump_type=pump_type,
        pm_latest=pm_latest,
        pm_history=pm_history,
        cm_latest=cm_latest,
        cm_history=cm_history,
        cmon_latest=cmon_latest,
        cmon_history=cmon_history,
        current_seal=current_seal,
        compatible_seals=compatible_seals,
        seal_stock=seal_stock,
        drawings=drawings,
        data_gaps=tuple(gaps),
    )


__all__ = ["Equipment360", "get_equipment_360"]

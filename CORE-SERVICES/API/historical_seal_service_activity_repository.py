"""MWO-LTSA-HISTORICAL-SEAL-SERVICE-ACTIVITY-001 -- repository for
reading historical mechanical seal service activity records (2024-2025).

HISTORY ONLY: These records are historical lifecycle/service events per pump
and must NOT establish or mutate the current mechanical-seal installation snapshot.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

_COLUMNS = (
    "activity_id, source_reference, source_type, source_year, source_filename, "
    "source_worksheet, source_row, source_job_document_number, sp_no, raw_tag, "
    "pump_tag_number, tag_match_outcome, raw_job_description, event_type, "
    "failure_attribution, seal_type, seal_size, drawing_number, quantity, "
    "shaft_sleeve_condition, gland_plate_condition, team_service, end_user, "
    "location, ltsa_area, unit_area, api_plan, pump_type, process_fluid, "
    "source_start_date, source_failure_date, finish_date, event_date, "
    "date_status, status, remarks, created_at"
)
# Governed-row selection shared by the per-pump and bulk reads (migration 039
# provenance present, admissible evidence grade, dated) -- one definition.
_GOVERNED_COLUMNS = (
    f"{_COLUMNS}, historical_event_id, position, evidence_grade, "
    "event_fingerprint, source_fingerprint, date_correction_status"
)
_GOVERNED_FILTER = (
    "historical_event_id IS NOT NULL "
    "AND evidence_grade IN ('DIRECT_EVIDENCE', 'CORROBORATED') AND event_date IS NOT NULL"
)


class HistoricalSealServiceActivityRepository:
    """Read-only access to historical seal service activities."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_by_pump(self, pump_tag_number: str) -> list[dict[str, Any]]:
        """Fetch historical service activity records linked to a canonical pump tag.
        Ordered chronologically by event_date ASC (Finish Date), then source_reference."""
        return _json_query(
            f"SELECT {_COLUMNS} FROM public.historical_seal_service_activity "
            f"WHERE pump_tag_number = {_sql(pump_tag_number)} "
            "ORDER BY event_date ASC NULLS LAST, source_reference ASC",
            self._runner,
        )

    def list_all(self) -> list[dict[str, Any]]:
        """Fetch all historical service activity records."""
        return _json_query(
            f"SELECT {_COLUMNS} FROM public.historical_seal_service_activity "
            "ORDER BY event_date ASC NULLS LAST, source_reference ASC",
            self._runner,
        )

    def list_governed_installation_events_by_pump(self, pump_tag_number: str) -> list[dict[str, Any]]:
        """LTSA_HISTORICAL_INSTALLATION_2024_2025_IMPORT_IMPLEMENTATION_R1 --
        only rows imported from the approved manifest (migration 039 governed
        provenance present), for the Installation-Based MTBF read model.
        Kept separate from list_by_pump() so the lifecycle timeline's column
        list works before and after migration 039."""
        return _json_query(
            f"SELECT {_GOVERNED_COLUMNS} FROM public.historical_seal_service_activity "
            f"WHERE pump_tag_number = {_sql(pump_tag_number)} AND {_GOVERNED_FILTER} "
            "ORDER BY event_date ASC, historical_event_id ASC",
            self._runner,
        )

    def list_governed_installation_events(self) -> list[dict[str, Any]]:
        """LTSA_POWER_BI_R1B -- bulk form of
        list_governed_installation_events_by_pump() for every pump in one
        query (same columns, same governed filter)."""
        return _json_query(
            f"SELECT {_GOVERNED_COLUMNS} FROM public.historical_seal_service_activity "
            f"WHERE pump_tag_number IS NOT NULL AND {_GOVERNED_FILTER} "
            "ORDER BY pump_tag_number, event_date ASC, historical_event_id ASC",
            self._runner,
        )

    def find_by_source_reference(self, source_reference: str) -> dict[str, Any] | None:
        """Find a single record by its idempotent source_reference key."""
        rows = _json_query(
            f"SELECT {_COLUMNS} FROM public.historical_seal_service_activity "
            f"WHERE source_reference = {_sql(source_reference)}",
            self._runner,
        )
        return rows[0] if rows else None


__all__ = ["HistoricalSealServiceActivityRepository"]

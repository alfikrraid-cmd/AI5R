"""Current Seal Installation Repository for LTSA.

Provides data access for public.current_seal_installation table.
Handles active records, resolution statuses, and equipment shaft positions.
Includes an in-memory implementation for test suites without a live database.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

try:
    from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402
except ImportError:
    _json_query = None
    _sql = None

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

_COLUMNS = (
    "id, pump_tag_number, equipment_side, seal_type, seal_size, drawing_no, "
    "assembly_gpn, material_code, source_type, source_reference, source_date, "
    "resolution_status, confidence_status, installed_at, removed_at, created_at, updated_at"
)


class CurrentSealInstallationRepositoryProtocol:
    """Protocol for current seal installation repository implementations."""

    def get_active_by_pump_tag(self, pump_tag: str) -> List[Dict[str, Any]]: ...
    def create_installation(self, **kwargs: Any) -> Dict[str, Any]: ...
    def list_active(self) -> List[Dict[str, Any]]: ...
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]: ...
    def supersede_installation(self, id: str, removed_at: Optional[str] = None) -> None: ...


class CurrentSealInstallationRepository:
    """PostgreSQL-backed Current Seal Installation Repository using canonical DatabaseRunner."""

    def __init__(self, runner: DatabaseRunner) -> None:
        self.runner = runner

    def get_active_by_pump_tag(self, pump_tag: str) -> List[Dict[str, Any]]:
        """Fetch all active (removed_at IS NULL) installation records for a pump."""
        sql = (
            f"SELECT {_COLUMNS} FROM public.current_seal_installation "
            f"WHERE pump_tag_number = {_sql(pump_tag)} AND removed_at IS NULL "
            f"ORDER BY created_at ASC"
        )
        try:
            return _json_query(sql, self.runner) if _json_query else []
        except Exception:
            # Safe fall-through if table does not exist yet (e.g. pre-migration R3A baseline)
            return []

    def create_installation(self, **kwargs: Any) -> Dict[str, Any]:
        """Insert a current seal installation record."""
        cols = [
            "pump_tag_number",
            "equipment_side",
            "seal_type",
            "seal_size",
            "drawing_no",
            "assembly_gpn",
            "material_code",
            "source_type",
            "source_reference",
            "source_date",
            "resolution_status",
            "confidence_status",
            "installed_at",
            "removed_at",
        ]
        present_cols = [c for c in cols if c in kwargs]
        val_sqls = [_sql(kwargs[c]) if kwargs[c] is not None else "NULL" for c in present_cols]

        sql = (
            f"INSERT INTO public.current_seal_installation ({', '.join(present_cols)}) "
            f"VALUES ({', '.join(val_sqls)}) "
            f"RETURNING {_COLUMNS}"
        )
        rows = _json_query(sql, self.runner) if _json_query else []
        return rows[0] if rows else {}

    def list_active(self) -> List[Dict[str, Any]]:
        """List all active installations across all pumps."""
        sql = (
            f"SELECT {_COLUMNS} FROM public.current_seal_installation "
            f"WHERE removed_at IS NULL ORDER BY pump_tag_number, equipment_side"
        )
        try:
            return _json_query(sql, self.runner) if _json_query else []
        except Exception:
            return []

    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        sql = f"SELECT {_COLUMNS} FROM public.current_seal_installation WHERE id = {_sql(id)}"
        try:
            rows = _json_query(sql, self.runner) if _json_query else []
            return rows[0] if rows else None
        except Exception:
            return None

    def supersede_installation(self, id: str, removed_at: Optional[str] = None) -> None:
        rem_val = removed_at or datetime.now(timezone.utc).isoformat()
        sql = (
            "UPDATE public.current_seal_installation "
            f"SET removed_at = {_sql(rem_val)}, updated_at = NOW() "
            f"WHERE id = {_sql(id)}"
        )
        if _json_query:
            _json_query(sql, self.runner)


class InMemoryCurrentSealInstallationRepository:
    """In-memory repository for unit and integration testing without database."""

    def __init__(self, initial_records: Optional[List[Dict[str, Any]]] = None) -> None:
        self.records: List[Dict[str, Any]] = [dict(r) for r in (initial_records or [])]

    def get_active_by_pump_tag(self, pump_tag: str) -> List[Dict[str, Any]]:
        return [
            dict(r)
            for r in self.records
            if r.get("pump_tag_number") == pump_tag and r.get("removed_at") is None
        ]

    def create_installation(self, **kwargs: Any) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        rec = {
            "id": kwargs.get("id", str(uuid.uuid4())),
            "pump_tag_number": kwargs.get("pump_tag_number"),
            "equipment_side": kwargs.get("equipment_side"),
            "seal_type": kwargs.get("seal_type"),
            "seal_size": kwargs.get("seal_size"),
            "drawing_no": kwargs.get("drawing_no"),
            "assembly_gpn": kwargs.get("assembly_gpn"),
            "material_code": kwargs.get("material_code"),
            "source_type": kwargs.get("source_type", "INSTALLATION_REPORT"),
            "source_reference": kwargs.get("source_reference"),
            "source_date": kwargs.get("source_date"),
            "resolution_status": kwargs.get("resolution_status", "CONFIRMED"),
            "confidence_status": kwargs.get("confidence_status", "CONFIRMED"),
            "installed_at": kwargs.get("installed_at"),
            "removed_at": kwargs.get("removed_at"),
            "created_at": now,
            "updated_at": now,
        }
        self.records.append(rec)
        return dict(rec)

    def list_active(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.records if r.get("removed_at") is None]

    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        for r in self.records:
            if str(r.get("id")) == str(id):
                return dict(r)
        return None

    def supersede_installation(self, id: str, removed_at: Optional[str] = None) -> None:
        rem_val = removed_at or datetime.now(timezone.utc).isoformat()
        for r in self.records:
            if str(r.get("id")) == str(id):
                r["removed_at"] = rem_val
                r["updated_at"] = rem_val
                break


__all__ = [
    "CurrentSealInstallationRepositoryProtocol",
    "CurrentSealInstallationRepository",
    "InMemoryCurrentSealInstallationRepository",
]


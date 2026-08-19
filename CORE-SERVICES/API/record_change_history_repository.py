"""MWO-LTSA-AUDIT-CHANGE-HISTORY-001 -- the ONE canonical, append-only
ledger for field-level corrections across every LTSA domain (CMON,
Installation, and any future PM/CM/master-data correction). No duplicate
ledger per domain.

Immutability is enforced by omission, not a DB trigger: this class
exposes ONLY append() and list_for_entity() -- there is no update()/
delete() method anywhere in this file, and no other file writes to
record_change_history. Nobody, including SUPERUSER, has a code path to
edit or delete an audit entry, per this MWO's own Hard Rule.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

_SELECT_COLUMNS = (
    "change_id, entity_type, entity_id, field_name, old_value, new_value, "
    "changed_by, changed_at, reason, source_reference"
)


class RecordChangeHistoryRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def append(
        self,
        *,
        entity_type: str,
        entity_id: str,
        field_name: str,
        old_value: str | None,
        new_value: str | None,
        changed_by: str,
        reason: str,
        source_reference: str | None = None,
    ) -> dict:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason, source_reference) "
                "VALUES ("
                f"{_sql(entity_type)}, {_sql(entity_id)}, {_sql(field_name)}, {_sql(old_value)}, "
                f"{_sql(new_value)}, {_sql(changed_by)}, {_sql(reason)}, {_sql(source_reference)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def list_for_entity(self, entity_type: str, entity_id: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM record_change_history "
            f"WHERE entity_type = {_sql(entity_type)} AND entity_id = {_sql(entity_id)} "
            "ORDER BY changed_at DESC",
            self._runner,
        )


__all__ = ["RecordChangeHistoryRepository"]

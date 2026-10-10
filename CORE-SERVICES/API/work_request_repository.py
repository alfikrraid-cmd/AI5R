"""LTSA_PERTAMINA_RBAC_SCOPE_AND_REQUEST_R2 -- ltsa_work_request (migration
055): PM / CM / Installation requests. A request is never a work order,
PM occurrence, CM report or installation record -- it only records that an
authorized user asked for the work. Direct-Postgres, same convention as
pm_occurrence_repository.py / operational_registry_repository.py.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .pump_area_scope import scope_sql_condition  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

REQUEST_TYPES: tuple[str, ...] = ("PM", "CM", "INSTALLATION")

_COLUMNS = "r.request_code, r.request_type, r.asset_code, r.description, r.status, r.requested_by, r.requested_at"


class WorkRequestRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def create(self, *, request_type: str, asset_code: str, description: str, requested_by: str) -> dict:
        request_code = f"WR-{uuid.uuid4().hex[:12].upper()}"
        # Data-modifying CTE at the top level (pm_occurrence_repository's own
        # convention); _json_query would nest the INSERT in a subquery.
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO public.ltsa_work_request (request_code, request_type, asset_code, description, requested_by) "
                f"VALUES ({_sql(request_code)}, {_sql(request_type)}, {_sql(asset_code)}, {_sql(description)}, {_sql(requested_by)}) "
                "RETURNING request_code, request_type, asset_code, description, status, requested_by, requested_at"
                ") SELECT COALESCE(json_agg(row_to_json(ins))::text, '[]') FROM ins;"
            )
            or "[]"
        )
        if not rows:
            raise RuntimeError("Work request was not created")
        return rows[0]

    def list_requests(self, *, scope: frozenset[str] | None = None) -> list[dict]:
        condition = scope_sql_condition(scope, "a.area", _sql)
        return _json_query(
            f"SELECT {_COLUMNS}, a.area "
            "FROM public.ltsa_work_request r JOIN public.asset_registry a ON a.asset_code = r.asset_code "
            f"{'WHERE ' + condition if condition else ''} "
            "ORDER BY r.requested_at DESC, r.request_code",
            self._runner,
        )

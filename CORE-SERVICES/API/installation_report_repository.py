"""
MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A -- InstallationReportRepository.

Root cause (Phase 1 audit): InstallationGateway.list_installations() calls
an n8n webhook (GET ltsa/installation/list) that was never registered in
production -- no workflow JSON for it exists anywhere in this repository
either, confirmed by repository search before writing this file. So this
is not "webhook inactive" (nothing to restore/redeploy) and not "route
path differs" (there is no route at all) -- it is a genuinely missing read
path. installation_report itself is real and populated (42 rows in
production, confirmed by direct read before writing this file) and is
already read directly (bypassing n8n) by installation_fitment_service.py's
own several narrow, single-record fitment queries -- this file follows
that exact same, already-working, already-canonical direct-DB pattern
(DatabaseRunner + _json_query, byte-for-byte the same helper
mechanical_seal_stock_repository.py also reuses), just as one small,
general-purpose "list every installation report" read that did not exist
anywhere yet (every existing direct-DB installation query is scoped to one
installation_code/pump_tag, not a fleet-wide list).

Read-only: this module contains no INSERT/UPDATE/DELETE/DDL statement
anywhere. list_installations()'s return shape is deliberately identical to
InstallationGateway.list_installations()'s own ({"success", "data"}) so
callers that already expect that shape (copilot_ask_service.py's fleet
installation handler) need no change beyond which object is injected.

Scope (disclosed): this repository is wired into Copilot's fleet-wide
"latest installation" query only (this MWO's own explicit scope). The
existing tag-scoped installation intent/handler and the
/api/ltsa/installations REST endpoint (Installation Workspace) keep using
the pre-existing InstallationGateway/n8n path unchanged -- fixing that
broader path is a separate concern this MWO does not touch ("DO NOT
redesign the intent router", "smallest safe correction").
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

# Real installation_report columns (CANONICAL_SCHEMA.sql) -- only the ones
# Copilot's fleet-installation answer actually needs (pump identity, real
# recorded date, seal identity for "useful seal information if recorded").
# No SELECT *: a fixed, disclosed column list, matching this file's own
# read-only, narrow-purpose scope.
_SELECT_COLUMNS = "installation_code, report_no, report_date, plant_equip_no, seal_code, seal_type"


class InstallationReportRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_installations(self) -> dict[str, Any]:
        rows = _json_query(f"SELECT {_SELECT_COLUMNS} FROM installation_report", self._runner)
        return {
            "success": True,
            "message": "Installation reports listed",
            "data": rows,
            "count": len(rows),
        }


__all__ = ["InstallationReportRepository"]

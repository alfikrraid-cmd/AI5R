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

list_installations()'s return shape is deliberately identical to
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

MWO-LTSA-INSTALLATION-REPORT-HISTORICAL-ATTRIBUTION-001 -- adds the three
read/write primitives installation_report_attribution_service.py's guard
logic needs (find_by_installation_code / count_canonical_pump_matches /
set_pump_tag_number_if_unset). This is document-level equipment
ATTRIBUTION only -- a plain pump_tag_number backfill from a report's own
already-recorded source_document_name -- never seal_unit_id/
installation_event_id/linked_by/link_reason, which stay exclusively
installation_fitment_service.py's job (physical fitment/lifecycle
linkage, a different, later, optional step). set_pump_tag_number_if_unset
is a guarded UPDATE ... WHERE pump_tag_number IS NULL, the same
one-guarded-write shape installation_fitment_service.link_installation_report
already established for this exact table.
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

    def find_by_installation_code(self, installation_code: str) -> dict[str, Any] | None:
        rows = _json_query(
            f"SELECT installation_code, pump_tag_number, source_document_name "
            f"FROM installation_report WHERE installation_code = {_sql(installation_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def count_canonical_pump_matches(self, pump_tag_number: str) -> int:
        rows = _json_query(
            f"SELECT count(*) AS n FROM ltsa_pumps WHERE tag_number = {_sql(pump_tag_number)}",
            self._runner,
        )
        return int(rows[0]["n"]) if rows else 0

    def set_pump_tag_number_if_unset(self, *, installation_code: str, pump_tag_number: str) -> dict[str, Any] | None:
        # Guarded, atomic: affects a row only if pump_tag_number is still
        # NULL at write time, mirroring installation_fitment_service.
        # link_installation_report()'s own guarded-UPDATE-with-RETURNING
        # shape for this same table. Never touches seal_unit_id/
        # installation_event_id/linked_by/link_reason/report_date/any
        # other column -- pure single-field attribution.
        script = f"""
WITH updated AS (
    UPDATE installation_report SET
        pump_tag_number = {_sql(pump_tag_number)},
        updated_at = NOW()
    WHERE installation_code = {_sql(installation_code)} AND pump_tag_number IS NULL
    RETURNING installation_code, pump_tag_number
)
SELECT COALESCE((SELECT json_agg(row_to_json(u))::text FROM updated u), '[]');
"""
        raw = self._runner.query_scalar(script.strip())
        rows = json.loads(raw or "[]")
        return rows[0] if rows else None

    def backfill_pump_tags_batch_atomic(self, mappings: list[dict[str, str]]) -> list[dict[str, Any]]:
        # MWO-LTSA-INSTALLATION-ATTRIBUTION-ATOMIC-BATCH-001 -- true
        # all-or-nothing across N rows in ONE call, no DatabaseRunner
        # change. DatabaseRunner's direct-connect mode already sends an
        # entire multi-statement script as one Postgres simple-query
        # message with autocommit=True -- Postgres itself treats that as
        # one implicit transaction unless the script's own BEGIN/COMMIT
        # says otherwise (the exact same "one script, one atomic outcome"
        # guarantee create_draft()/link_installation_report() already
        # rely on for a single guarded write; this reuses it for N).
        #
        # Shape: BEGIN -> precheck DO block (RAISE EXCEPTION if any of
        # the N targets is missing/already-linked/unknown-pump/ambiguous
        # -- aborts before any UPDATE runs) -> ONE UPDATE ... FROM
        # (VALUES ...) covering all N rows, still individually guarded by
        # WHERE pump_tag_number IS NULL -> postcheck DO block (RAISE
        # EXCEPTION unless exactly len(mappings) rows ended up linked --
        # catches a same-millisecond race the precheck couldn't see) ->
        # COMMIT -> final SELECT of the resulting rows. Any RAISE
        # EXCEPTION anywhere before COMMIT aborts the whole script; the
        # trailing COMMIT/SELECT never execute; psycopg2 raises the
        # server error back to the caller. Postcondition is always
        # exactly 0-of-N or N-of-N linked, never partial.
        if not mappings:
            return []

        codes = [m["installation_code"] for m in mappings]
        values_sql = ", ".join(
            f"({_sql(m['installation_code'])}, {_sql(m['pump_tag_number'])})" for m in mappings
        )
        codes_sql = ", ".join(_sql(c) for c in codes)
        n = len(mappings)

        script = f"""
BEGIN;

DO $$
DECLARE
  v_bad_count INT;
BEGIN
  SELECT count(*) INTO v_bad_count
  FROM (VALUES {values_sql}) AS m(installation_code, target_tag)
  LEFT JOIN installation_report r ON r.installation_code = m.installation_code
  LEFT JOIN (SELECT tag_number, count(*) AS c FROM ltsa_pumps GROUP BY tag_number) p
    ON p.tag_number = m.target_tag
  WHERE r.installation_code IS NULL
     OR r.pump_tag_number IS NOT NULL
     OR p.tag_number IS NULL
     OR p.c <> 1;
  IF v_bad_count > 0 THEN
    RAISE EXCEPTION 'installation attribution precheck failed for % of {n} targets', v_bad_count;
  END IF;
END $$;

UPDATE installation_report SET
    pump_tag_number = m.target_tag,
    updated_at = NOW()
FROM (VALUES {values_sql}) AS m(installation_code, target_tag)
WHERE installation_report.installation_code = m.installation_code
  AND installation_report.pump_tag_number IS NULL;

DO $$
DECLARE
  v_linked_count INT;
BEGIN
  SELECT count(*) INTO v_linked_count FROM installation_report
  WHERE installation_code IN ({codes_sql}) AND pump_tag_number IS NOT NULL;
  IF v_linked_count <> {n} THEN
    RAISE EXCEPTION 'installation attribution postcheck failed: % of {n} linked', v_linked_count;
  END IF;
END $$;

COMMIT;

SELECT COALESCE((SELECT json_agg(row_to_json(t))::text FROM (
    SELECT installation_code, pump_tag_number FROM installation_report
    WHERE installation_code IN ({codes_sql}) ORDER BY installation_code
) t), '[]');
"""
        # Not _json_query: that helper wraps its input as a single SELECT
        # subquery, which cannot hold a BEGIN/DO/UPDATE/COMMIT script.
        # query_scalar() sends the script verbatim, exactly like
        # set_pump_tag_number_if_unset()/create_draft() already do.
        raw = self._runner.query_scalar(script.strip())
        return json.loads(raw or "[]")


__all__ = ["InstallationReportRepository"]

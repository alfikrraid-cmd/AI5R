"""MWO-LTSA-DRAWING-INPUT-R4 -- real Postgres persistence for the
canonical Engineering Drawing schema (migration 038, Drawing-R3):
engineering_drawing, engineering_drawing_revision,
engineering_drawing_revision_artifact, engineering_drawing_link,
engineering_drawing_bom_line. One cohesive repository (not one file per
table) -- the five entities are always read/written together for a
single logical drawing, mirroring how ContractCoverageService/
LtsaContractRepository already group contract+scope in one module.

Same direct-Postgres, CTE-shaped INSERT/UPDATE...RETURNING + a
record_change_history audit row style as ltsa_finding_repository.py /
condition_monitoring_measurement_repository.py -- no parallel repository
framework introduced.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


# ---- domain exceptions -- each maps 1:1 to a distinct R4 validation rule ----

class DrawingNotFound(Exception):
    """drawing_code supplied to create a child row (revision/link) does
    not exist. Distinct from a plain None return, which this repository
    reserves for 'the row you asked to fetch/update by its own primary
    key does not exist'."""


class RevisionNotFound(Exception):
    """revision_code supplied to create a child row (artifact/BOM line)
    does not exist."""


class KnowledgeSourceNotFound(Exception):
    """knowledge_source_id supplied to create an artifact does not exist
    in knowledge_source_registry -- R4 Section 6's own explicit
    'knowledge_source_id must exist' requirement."""


class ArtifactNotFound(Exception):
    """derived_from_artifact_code supplied does not exist."""


class ComponentNotFound(Exception):
    """component_id supplied to a BOM line does not exist in
    internal_component_master."""


class CrossDrawingRevision(Exception):
    """set_current_revision's revision_code does not belong to the
    target drawing_code -- pre-checked here for a clean error rather
    than relying on the DB's own composite-FK violation, though that FK
    remains the final defense (R3's own current_revision_fkey)."""


class InvalidLinkTarget(Exception):
    """target_code does not resolve against target_type's exact
    canonical authority (asset_registry/seal_registry/
    internal_component_master) -- no fuzzy matching, no alias inference
    (R4 Section 9's own explicit prohibition)."""


class DuplicateActiveLink(Exception):
    """The DB's own partial unique index
    (idx_engineering_drawing_link_active_unique) rejected an identical
    active (drawing_code, target_type, target_code, relationship_type)
    tuple."""


class DuplicatePrimaryArtifact(Exception):
    """The DB's own partial unique index
    (idx_engineering_drawing_revision_artifact_one_primary) rejected a
    second is_primary=TRUE row for the same (revision_code,
    artifact_class)."""


_VERIFICATION_STATUS_VALUES = ("DRAFT", "UNDER_REVIEW", "VERIFIED", "CANONICAL")
_ARTIFACT_CLASS_VALUES = ("SOURCE_DOCUMENT", "SOURCE_CAD", "DERIVED_CAD", "VIEWER_ASSET", "UNKNOWN")
_TARGET_TYPE_VALUES = ("ASSET", "SEAL", "COMPONENT")
_RELATIONSHIP_TYPE_VALUES = ("APPLIES_TO", "DEPICTS", "COMPONENT_OF")

# Polymorphic target validation (R4 Section 9) -- exact canonical key per
# target_type, no fuzzy matching, no alias inference. Extending this map
# is the ONLY change needed if a future target_type is ever approved.
_TARGET_AUTHORITY = {
    "ASSET": ("asset_registry", "asset_code"),
    "SEAL": ("seal_registry", "seal_code"),
    "COMPONENT": ("internal_component_master", "component_id"),
}

_DRAWING_SELECT_COLUMNS = (
    "drawing_code, drawing_number, title, manufacturer, drawing_type, current_revision_code, "
    "created_at, created_by, updated_at, updated_by"
)
_REVISION_SELECT_COLUMNS = (
    "revision_code, drawing_code, revision, revision_date, verification_status, supersedes_revision_code, "
    "notes, created_at, created_by, updated_at, updated_by"
)
_ARTIFACT_SELECT_COLUMNS = (
    "artifact_code, revision_code, knowledge_source_id, artifact_class, is_primary, derived_from_artifact_code, "
    "verification_status, created_at, created_by, updated_at, updated_by"
)
_LINK_SELECT_COLUMNS = (
    "link_code, drawing_code, target_type, target_code, relationship_type, verification_status, "
    "source_reference, retracted_at, retracted_by, created_at, created_by, updated_at, updated_by"
)
_BOM_SELECT_COLUMNS = (
    "bom_line_code, revision_code, item_position, component_id, component_description, quantity, "
    "material_or_specification, notes, created_at, created_by, updated_at, updated_by"
)

_DRAWING_UPDATABLE = ("drawing_number", "title", "manufacturer", "drawing_type")
_REVISION_UPDATABLE = ("revision", "revision_date", "verification_status", "supersedes_revision_code", "notes")
# artifact_class is DELIBERATELY excluded -- immutable through PATCH (R4
# Section 6). A caller attempting to change it has that attempt silently
# dropped (never applied), so the row's own provenance classification
# never changes in place -- a corrected classification is always a NEW
# artifact row, never a rewrite of this one.
_ARTIFACT_UPDATABLE = ("is_primary", "verification_status")
_BOM_UPDATABLE = ("item_position", "component_id", "component_description", "quantity", "material_or_specification", "notes")


def _new_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def _validate_enum(value: str | None, allowed: tuple[str, ...], field: str) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f"invalid {field}: {value!r} (allowed: {', '.join(allowed)})")


class EngineeringDrawingRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    # ---- shared existence helpers ----

    def _exists(self, table: str, column: str, value: str) -> bool:
        rows = _json_query(f"SELECT 1 AS ok FROM {table} WHERE {column} = {_sql(value)}", self._runner)
        return bool(rows)

    def _drawing_exists(self, drawing_code: str) -> bool:
        return self._exists("engineering_drawing", "drawing_code", drawing_code)

    def _revision_row(self, revision_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_REVISION_SELECT_COLUMNS} FROM engineering_drawing_revision WHERE revision_code = {_sql(revision_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def _validate_target(self, target_type: str, target_code: str) -> None:
        table, column = _TARGET_AUTHORITY[target_type]
        if not self._exists(table, column, target_code):
            raise InvalidLinkTarget(f"{target_type}:{target_code} does not exist in {table}.{column}")

    def _drawing_area_scope_clause(self, alias: str, scope: frozenset[str] | None) -> str:
        # R4 Section 16: a drawing has no direct area of its own -- scope
        # is derived exclusively from its ACTIVE ASSET links, joined to
        # asset_registry.area. A drawing with no ASSET link at all (e.g.
        # SEAL/COMPONENT-only) has no determinable area and is EXCLUDED
        # for any restricted (non-None scope) identity -- fail-closed,
        # the same convention routers/document.py already established
        # for a seal with zero compatibility rows ("resolves to zero
        # areas -- fail-closed"). Never guessed, never a fabricated MA.
        if scope is None:
            return "TRUE"
        if not scope:
            return "FALSE"
        values = ", ".join(_sql(area) for area in sorted(scope))
        return (
            f"EXISTS (SELECT 1 FROM engineering_drawing_link l JOIN asset_registry a "
            f"ON a.asset_code = l.target_code WHERE l.drawing_code = {alias}.drawing_code "
            f"AND l.target_type = 'ASSET' AND l.retracted_at IS NULL AND a.area IN ({values}))"
        )

    def is_drawing_in_scope(self, drawing_code: str, scope: frozenset[str] | None) -> bool:
        if scope is None:
            return True
        clause = self._drawing_area_scope_clause("d", scope)
        rows = _json_query(
            f"SELECT 1 AS ok FROM engineering_drawing d WHERE d.drawing_code = {_sql(drawing_code)} AND {clause}",
            self._runner,
        )
        return bool(rows)

    # ================= DRAWING =================

    def create_drawing(
        self, *, drawing_number: str | None = None, title: str, manufacturer: str | None = None,
        drawing_type: str | None = None, created_by: str,
    ) -> dict:
        code = _new_code("ENGDRW")
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO engineering_drawing (drawing_code, drawing_number, title, manufacturer, drawing_type, created_by, updated_by) "
                f"VALUES ({_sql(code)}, {_sql(drawing_number)}, {_sql(title)}, {_sql(manufacturer)}, {_sql(drawing_type)}, "
                f"{_sql(created_by)}, {_sql(created_by)}) "
                f"RETURNING {_DRAWING_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'ENGINEERING_DRAWING', drawing_code, '__record__', NULL, row_to_json(ins)::text, "
                f"{_sql(created_by)}, 'CREATE' FROM ins) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def find_drawing(self, drawing_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_DRAWING_SELECT_COLUMNS} FROM engineering_drawing WHERE drawing_code = {_sql(drawing_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_drawings(self, *, scope: frozenset[str] | None = None, limit: int = 25, offset: int = 0) -> dict:
        clause = self._drawing_area_scope_clause("d", scope)
        rows = _json_query(
            f"SELECT {', '.join(f'd.{c.strip()}' for c in _DRAWING_SELECT_COLUMNS.split(','))} "
            f"FROM engineering_drawing d WHERE {clause} ORDER BY d.created_at DESC "
            f"LIMIT {int(limit)} OFFSET {int(offset)}",
            self._runner,
        )
        total = int(
            (_json_query(f"SELECT COUNT(*) AS total FROM engineering_drawing d WHERE {clause}", self._runner) or [{"total": 0}])[0]["total"]
        )
        return {"success": True, "data": rows, "items": rows, "count": len(rows), "total": total, "limit": limit, "offset": offset}

    def update_drawing(self, drawing_code: str, *, values: dict, updated_by: str) -> dict | None:
        existing = self.find_drawing(drawing_code)
        if existing is None:
            return None
        changes = {k: v for k, v in values.items() if k in _DRAWING_UPDATABLE}
        if not changes:
            return existing
        set_sql = ", ".join(f"{col} = {_sql(val)}" for col, val in changes.items())
        rows = json.loads(
            self._runner.query_scalar(
                "WITH old AS (SELECT row_to_json(r)::text AS snapshot FROM engineering_drawing r "
                f"WHERE drawing_code = {_sql(drawing_code)}), upd AS ("
                f"UPDATE engineering_drawing SET {set_sql}, updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE drawing_code = {_sql(drawing_code)} RETURNING {_DRAWING_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'ENGINEERING_DRAWING', drawing_code, '__record__', old.snapshot, row_to_json(upd)::text, "
                f"{_sql(updated_by)}, 'UPDATE' FROM upd CROSS JOIN old) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def set_current_revision(self, drawing_code: str, revision_code: str, *, updated_by: str) -> dict | None:
        drawing = self.find_drawing(drawing_code)
        if drawing is None:
            return None
        revision = self._revision_row(revision_code)
        if revision is None:
            raise RevisionNotFound(revision_code)
        if revision["drawing_code"] != drawing_code:
            raise CrossDrawingRevision(f"revision {revision_code} belongs to drawing {revision['drawing_code']}, not {drawing_code}")
        rows = json.loads(
            self._runner.query_scalar(
                "WITH old AS (SELECT row_to_json(r)::text AS snapshot FROM engineering_drawing r "
                f"WHERE drawing_code = {_sql(drawing_code)}), upd AS ("
                f"UPDATE engineering_drawing SET current_revision_code = {_sql(revision_code)}, "
                f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE drawing_code = {_sql(drawing_code)} RETURNING {_DRAWING_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'ENGINEERING_DRAWING', drawing_code, 'current_revision_code', old.snapshot, row_to_json(upd)::text, "
                f"{_sql(updated_by)}, 'UPDATE' FROM upd CROSS JOIN old) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    # ================= REVISION =================

    def create_revision(
        self, *, drawing_code: str, revision: str | None = None, revision_date: str | None = None,
        verification_status: str = "DRAFT", supersedes_revision_code: str | None = None,
        notes: str | None = None, created_by: str,
    ) -> dict:
        if not self._drawing_exists(drawing_code):
            raise DrawingNotFound(drawing_code)
        _validate_enum(verification_status, _VERIFICATION_STATUS_VALUES, "verification_status")
        if supersedes_revision_code is not None:
            superseded = self._revision_row(supersedes_revision_code)
            if superseded is None:
                raise RevisionNotFound(supersedes_revision_code)
            if superseded["drawing_code"] != drawing_code:
                raise CrossDrawingRevision(
                    f"supersedes_revision_code {supersedes_revision_code} belongs to a different drawing"
                )

        code = _new_code("ENGDRWREV")
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO engineering_drawing_revision "
                "(revision_code, drawing_code, revision, revision_date, verification_status, supersedes_revision_code, notes, created_by, updated_by) "
                f"VALUES ({_sql(code)}, {_sql(drawing_code)}, {_sql(revision)}, {_sql(revision_date)}, "
                f"{_sql(verification_status)}, {_sql(supersedes_revision_code)}, {_sql(notes)}, "
                f"{_sql(created_by)}, {_sql(created_by)}) "
                f"RETURNING {_REVISION_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'ENGINEERING_DRAWING_REVISION', revision_code, '__record__', NULL, row_to_json(ins)::text, "
                f"{_sql(created_by)}, 'CREATE' FROM ins) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def find_revision(self, revision_code: str) -> dict | None:
        return self._revision_row(revision_code)

    def list_revisions_for_drawing(self, drawing_code: str) -> list[dict] | None:
        if not self._drawing_exists(drawing_code):
            return None
        return _json_query(
            f"SELECT {_REVISION_SELECT_COLUMNS} FROM engineering_drawing_revision "
            f"WHERE drawing_code = {_sql(drawing_code)} ORDER BY created_at",
            self._runner,
        )

    def update_revision(self, revision_code: str, *, values: dict, updated_by: str) -> dict | None:
        existing = self._revision_row(revision_code)
        if existing is None:
            return None
        changes = {k: v for k, v in values.items() if k in _REVISION_UPDATABLE}
        if not changes:
            return existing
        if "verification_status" in changes:
            _validate_enum(changes["verification_status"], _VERIFICATION_STATUS_VALUES, "verification_status")
        if "supersedes_revision_code" in changes and changes["supersedes_revision_code"] is not None:
            superseded = self._revision_row(changes["supersedes_revision_code"])
            if superseded is None:
                raise RevisionNotFound(changes["supersedes_revision_code"])
            if superseded["drawing_code"] != existing["drawing_code"]:
                raise CrossDrawingRevision("supersedes_revision_code belongs to a different drawing")

        set_sql = ", ".join(f"{col} = {_sql(val)}" for col, val in changes.items())
        rows = json.loads(
            self._runner.query_scalar(
                "WITH old AS (SELECT row_to_json(r)::text AS snapshot FROM engineering_drawing_revision r "
                f"WHERE revision_code = {_sql(revision_code)}), upd AS ("
                f"UPDATE engineering_drawing_revision SET {set_sql}, updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE revision_code = {_sql(revision_code)} RETURNING {_REVISION_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'ENGINEERING_DRAWING_REVISION', revision_code, '__record__', old.snapshot, row_to_json(upd)::text, "
                f"{_sql(updated_by)}, 'UPDATE' FROM upd CROSS JOIN old) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    # ================= ARTIFACT =================

    def create_artifact(
        self, *, revision_code: str, knowledge_source_id: str, artifact_class: str = "UNKNOWN",
        is_primary: bool = False, derived_from_artifact_code: str | None = None,
        verification_status: str = "DRAFT", created_by: str,
    ) -> dict:
        if self._revision_row(revision_code) is None:
            raise RevisionNotFound(revision_code)
        if not self._exists("knowledge_source_registry", "knowledge_source_id", knowledge_source_id):
            raise KnowledgeSourceNotFound(knowledge_source_id)
        _validate_enum(artifact_class, _ARTIFACT_CLASS_VALUES, "artifact_class")
        _validate_enum(verification_status, _VERIFICATION_STATUS_VALUES, "verification_status")
        if derived_from_artifact_code is not None and not self._exists(
            "engineering_drawing_revision_artifact", "artifact_code", derived_from_artifact_code
        ):
            raise ArtifactNotFound(derived_from_artifact_code)

        code = _new_code("ENGART")
        try:
            rows = json.loads(
                self._runner.query_scalar(
                    "WITH ins AS ("
                    "INSERT INTO engineering_drawing_revision_artifact "
                    "(artifact_code, revision_code, knowledge_source_id, artifact_class, is_primary, derived_from_artifact_code, verification_status, created_by, updated_by) "
                    f"VALUES ({_sql(code)}, {_sql(revision_code)}, {_sql(knowledge_source_id)}, {_sql(artifact_class)}, "
                    f"{_sql(is_primary)}, {_sql(derived_from_artifact_code)}, {_sql(verification_status)}, "
                    f"{_sql(created_by)}, {_sql(created_by)}) "
                    f"RETURNING {_ARTIFACT_SELECT_COLUMNS}"
                    "), audit AS (INSERT INTO record_change_history "
                    "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                    "SELECT 'ENGINEERING_DRAWING_REVISION_ARTIFACT', artifact_code, '__record__', NULL, row_to_json(ins)::text, "
                    f"{_sql(created_by)}, 'CREATE' FROM ins) "
                    "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
                )
                or "[]"
            )
        except Exception as exc:  # noqa: BLE001
            if "idx_engineering_drawing_revision_artifact_one_primary" in str(exc):
                raise DuplicatePrimaryArtifact(f"{revision_code}:{artifact_class}") from exc
            raise
        return rows[0]

    def find_artifact(self, artifact_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_ARTIFACT_SELECT_COLUMNS} FROM engineering_drawing_revision_artifact WHERE artifact_code = {_sql(artifact_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_artifacts_for_revision(self, revision_code: str) -> list[dict] | None:
        if self._revision_row(revision_code) is None:
            return None
        return _json_query(
            f"SELECT {_ARTIFACT_SELECT_COLUMNS} FROM engineering_drawing_revision_artifact "
            f"WHERE revision_code = {_sql(revision_code)} ORDER BY created_at",
            self._runner,
        )

    def update_artifact(self, artifact_code: str, *, values: dict, updated_by: str) -> dict | None:
        existing = self.find_artifact(artifact_code)
        if existing is None:
            return None
        # artifact_class silently dropped if present -- see _ARTIFACT_UPDATABLE's own comment.
        changes = {k: v for k, v in values.items() if k in _ARTIFACT_UPDATABLE}
        if not changes:
            return existing
        if "verification_status" in changes:
            _validate_enum(changes["verification_status"], _VERIFICATION_STATUS_VALUES, "verification_status")

        set_sql = ", ".join(f"{col} = {_sql(val)}" for col, val in changes.items())
        try:
            rows = json.loads(
                self._runner.query_scalar(
                    "WITH old AS (SELECT row_to_json(r)::text AS snapshot FROM engineering_drawing_revision_artifact r "
                    f"WHERE artifact_code = {_sql(artifact_code)}), upd AS ("
                    f"UPDATE engineering_drawing_revision_artifact SET {set_sql}, updated_by = {_sql(updated_by)}, updated_at = NOW() "
                    f"WHERE artifact_code = {_sql(artifact_code)} RETURNING {_ARTIFACT_SELECT_COLUMNS}"
                    "), audit AS (INSERT INTO record_change_history "
                    "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                    "SELECT 'ENGINEERING_DRAWING_REVISION_ARTIFACT', artifact_code, '__record__', old.snapshot, row_to_json(upd)::text, "
                    f"{_sql(updated_by)}, 'UPDATE' FROM upd CROSS JOIN old) "
                    "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
                )
                or "[]"
            )
        except Exception as exc:  # noqa: BLE001
            if "idx_engineering_drawing_revision_artifact_one_primary" in str(exc):
                raise DuplicatePrimaryArtifact(artifact_code) from exc
            raise
        return rows[0] if rows else None

    # ================= LINK =================

    def create_link(
        self, *, drawing_code: str, target_type: str, target_code: str, relationship_type: str,
        verification_status: str = "DRAFT", source_reference: str | None = None, created_by: str,
    ) -> dict:
        if not self._drawing_exists(drawing_code):
            raise DrawingNotFound(drawing_code)
        _validate_enum(target_type, _TARGET_TYPE_VALUES, "target_type")
        _validate_enum(relationship_type, _RELATIONSHIP_TYPE_VALUES, "relationship_type")
        _validate_enum(verification_status, _VERIFICATION_STATUS_VALUES, "verification_status")
        self._validate_target(target_type, target_code)

        code = _new_code("ENGLINK")
        try:
            rows = json.loads(
                self._runner.query_scalar(
                    "WITH ins AS ("
                    "INSERT INTO engineering_drawing_link "
                    "(link_code, drawing_code, target_type, target_code, relationship_type, verification_status, source_reference, created_by, updated_by) "
                    f"VALUES ({_sql(code)}, {_sql(drawing_code)}, {_sql(target_type)}, {_sql(target_code)}, "
                    f"{_sql(relationship_type)}, {_sql(verification_status)}, {_sql(source_reference)}, "
                    f"{_sql(created_by)}, {_sql(created_by)}) "
                    f"RETURNING {_LINK_SELECT_COLUMNS}"
                    "), audit AS (INSERT INTO record_change_history "
                    "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                    "SELECT 'ENGINEERING_DRAWING_LINK', link_code, '__record__', NULL, row_to_json(ins)::text, "
                    f"{_sql(created_by)}, 'CREATE' FROM ins) "
                    "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
                )
                or "[]"
            )
        except Exception as exc:  # noqa: BLE001
            if "idx_engineering_drawing_link_active_unique" in str(exc):
                raise DuplicateActiveLink(f"{drawing_code}:{target_type}:{target_code}:{relationship_type}") from exc
            raise
        return rows[0]

    def find_link(self, link_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_LINK_SELECT_COLUMNS} FROM engineering_drawing_link WHERE link_code = {_sql(link_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_links_for_drawing(self, drawing_code: str, *, include_retracted: bool = False) -> list[dict] | None:
        if not self._drawing_exists(drawing_code):
            return None
        retracted_clause = "" if include_retracted else "AND retracted_at IS NULL"
        return _json_query(
            f"SELECT {_LINK_SELECT_COLUMNS} FROM engineering_drawing_link "
            f"WHERE drawing_code = {_sql(drawing_code)} {retracted_clause} ORDER BY created_at",
            self._runner,
        )

    def retract_link(self, link_code: str, *, retracted_by: str) -> dict | None:
        existing = self.find_link(link_code)
        if existing is None:
            return None
        if existing["retracted_at"] is not None:
            return existing  # idempotent -- never overwrite the original retraction timestamp
        rows = json.loads(
            self._runner.query_scalar(
                "WITH old AS (SELECT row_to_json(r)::text AS snapshot FROM engineering_drawing_link r "
                f"WHERE link_code = {_sql(link_code)}), upd AS ("
                f"UPDATE engineering_drawing_link SET retracted_at = NOW(), retracted_by = {_sql(retracted_by)}, "
                f"updated_by = {_sql(retracted_by)}, updated_at = NOW() "
                f"WHERE link_code = {_sql(link_code)} RETURNING {_LINK_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'ENGINEERING_DRAWING_LINK', link_code, 'retracted_at', old.snapshot, row_to_json(upd)::text, "
                f"{_sql(retracted_by)}, 'RETRACT' FROM upd CROSS JOIN old) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    # ================= BOM =================

    def create_bom_line(
        self, *, revision_code: str, item_position: str | None = None, component_id: str | None = None,
        component_description: str | None = None, quantity: float | None = None,
        material_or_specification: str | None = None, notes: str | None = None, created_by: str,
    ) -> dict:
        if self._revision_row(revision_code) is None:
            raise RevisionNotFound(revision_code)
        if component_id is not None and not self._exists("internal_component_master", "component_id", component_id):
            raise ComponentNotFound(component_id)

        code = _new_code("ENGBOM")
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO engineering_drawing_bom_line "
                "(bom_line_code, revision_code, item_position, component_id, component_description, quantity, material_or_specification, notes, created_by, updated_by) "
                f"VALUES ({_sql(code)}, {_sql(revision_code)}, {_sql(item_position)}, {_sql(component_id)}, "
                f"{_sql(component_description)}, {_sql(quantity)}, {_sql(material_or_specification)}, {_sql(notes)}, "
                f"{_sql(created_by)}, {_sql(created_by)}) "
                f"RETURNING {_BOM_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'ENGINEERING_DRAWING_BOM_LINE', bom_line_code, '__record__', NULL, row_to_json(ins)::text, "
                f"{_sql(created_by)}, 'CREATE' FROM ins) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def find_bom_line(self, bom_line_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_BOM_SELECT_COLUMNS} FROM engineering_drawing_bom_line WHERE bom_line_code = {_sql(bom_line_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_bom_for_revision(self, revision_code: str) -> list[dict] | None:
        if self._revision_row(revision_code) is None:
            return None
        return _json_query(
            f"SELECT {_BOM_SELECT_COLUMNS} FROM engineering_drawing_bom_line "
            f"WHERE revision_code = {_sql(revision_code)} ORDER BY created_at",
            self._runner,
        )

    def update_bom_line(self, bom_line_code: str, *, values: dict, updated_by: str) -> dict | None:
        existing = self.find_bom_line(bom_line_code)
        if existing is None:
            return None
        changes = {k: v for k, v in values.items() if k in _BOM_UPDATABLE}
        if not changes:
            return existing
        if "component_id" in changes and changes["component_id"] is not None:
            if not self._exists("internal_component_master", "component_id", changes["component_id"]):
                raise ComponentNotFound(changes["component_id"])

        set_sql = ", ".join(f"{col} = {_sql(val)}" for col, val in changes.items())
        rows = json.loads(
            self._runner.query_scalar(
                "WITH old AS (SELECT row_to_json(r)::text AS snapshot FROM engineering_drawing_bom_line r "
                f"WHERE bom_line_code = {_sql(bom_line_code)}), upd AS ("
                f"UPDATE engineering_drawing_bom_line SET {set_sql}, updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE bom_line_code = {_sql(bom_line_code)} RETURNING {_BOM_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'ENGINEERING_DRAWING_BOM_LINE', bom_line_code, '__record__', old.snapshot, row_to_json(upd)::text, "
                f"{_sql(updated_by)}, 'UPDATE' FROM upd CROSS JOIN old) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    # ================= READ MODEL (R4 Section 13) =================

    def get_drawing_detail(self, drawing_code: str, *, include_retracted_links: bool = False) -> dict | None:
        drawing = self.find_drawing(drawing_code)
        if drawing is None:
            return None
        revisions = self.list_revisions_for_drawing(drawing_code) or []
        artifacts_by_revision = {
            rev["revision_code"]: (self.list_artifacts_for_revision(rev["revision_code"]) or []) for rev in revisions
        }
        bom_by_revision = {
            rev["revision_code"]: (self.list_bom_for_revision(rev["revision_code"]) or []) for rev in revisions
        }
        links = self.list_links_for_drawing(drawing_code, include_retracted=include_retracted_links) or []
        current_revision = next((r for r in revisions if r["revision_code"] == drawing["current_revision_code"]), None)
        return {
            "drawing": drawing,
            "current_revision": current_revision,
            "revisions": revisions,
            "artifacts_by_revision": artifacts_by_revision,
            "bom_by_revision": bom_by_revision,
            "links": links,
        }


__all__ = [
    "EngineeringDrawingRepository",
    "DrawingNotFound",
    "RevisionNotFound",
    "KnowledgeSourceNotFound",
    "ArtifactNotFound",
    "ComponentNotFound",
    "CrossDrawingRevision",
    "InvalidLinkTarget",
    "DuplicateActiveLink",
    "DuplicatePrimaryArtifact",
]

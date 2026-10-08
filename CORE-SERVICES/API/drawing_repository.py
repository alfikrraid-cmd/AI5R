"""Drawing Repository for LTSA Mechanical Seal Engineering Drawings.

Provides data access for public.seal_engineering_document and
public.drawing_engineering_link tables.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

_DOCUMENT_COLUMNS = (
    "document_code, seal_code, document_type, document_number, title, revision, "
    "object_key, sha256_checksum, file_size_bytes, content_type, file_name, "
    "uploaded_by, provenance, revision_status, is_current_revision, superseded_at, "
    "superseded_by_document_code, drawing_generation, "
    "status, created_at, updated_at"
)

_LINK_COLUMNS = (
    "link_id, document_code, drawing_number, raw_reference, normalized_reference, "
    "target_type, target_code, equipment_side, source_type, source_record_id, evidence_method, "
    "confidence_status, notes, created_by, created_at, updated_at"
)


class DrawingRepositoryProtocol:
    """Protocol for drawing repository implementations."""

    def create_document(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_document_by_code(self, document_code: str) -> dict[str, Any] | None: ...
    def get_document_by_number_and_revision(self, drawing_number: str, revision: str) -> dict[str, Any] | None: ...
    def find_by_checksum(self, sha256_checksum: str) -> dict[str, Any] | None: ...
    def list_documents(self, **filters: Any) -> list[dict[str, Any]]: ...
    def list_revisions(self, drawing_number: str) -> list[dict[str, Any]]: ...
    def supersede_previous_revisions(self, drawing_number: str, keep_current_code: str) -> None: ...
    def update_status(self, document_code: str, status: str, is_current_revision: bool) -> dict[str, Any] | None: ...
    def set_lineage(self, legacy_document_code: str, superseded_by_document_code: str) -> dict[str, Any] | None: ...
    def create_link(self, **kwargs: Any) -> dict[str, Any]: ...
    def list_links_for_document(self, document_code: str) -> list[dict[str, Any]]: ...
    def list_links_for_drawing_number(self, drawing_number: str) -> list[dict[str, Any]]: ...
    def list_links_for_target(self, target_type: str, target_code: str) -> list[dict[str, Any]]: ...
    def list_drawings_for_target(self, target_code: str, target_type: str = "PUMP") -> list[dict[str, Any]]: ...


class DrawingRepository:
    """PostgreSQL-backed Drawing Repository using canonical DatabaseRunner."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def create_document(
        self,
        *,
        document_code: str,
        drawing_number: str,
        title: str,
        revision: str,
        object_key: str,
        sha256_checksum: str,
        file_size_bytes: int,
        content_type: str,
        file_name: str,
        uploaded_by: str | None = None,
        seal_code: str | None = None,
        provenance: str = "MANUAL",
        revision_status: str = "PENDING_REVIEW",
        is_current_revision: bool = False,
        superseded_by_document_code: str | None = None,
        drawing_generation: str | None = None,
        status: str = "APPROVED",
    ) -> dict[str, Any]:
        superseded_by_sql = _sql(superseded_by_document_code) if superseded_by_document_code else "NULL"
        generation_sql = _sql(drawing_generation) if drawing_generation else "NULL"
        sql = (
            "INSERT INTO public.seal_engineering_document "
            "(document_code, document_type, document_number, title, revision, object_key, "
            "sha256_checksum, file_size_bytes, content_type, file_name, uploaded_by, "
            "seal_code, provenance, revision_status, is_current_revision, superseded_by_document_code, drawing_generation, status) "
            "VALUES ("
            f"{_sql(document_code)}, 'DRAWING', {_sql(drawing_number)}, {_sql(title)}, {_sql(revision)}, "
            f"{_sql(object_key)}, {_sql(sha256_checksum)}, {file_size_bytes}, {_sql(content_type)}, "
            f"{_sql(file_name)}, {_sql(uploaded_by)}, {_sql(seal_code)}, {_sql(provenance)}, "
            f"{_sql(revision_status)}, {'TRUE' if is_current_revision else 'FALSE'}, {superseded_by_sql}, {generation_sql}, {_sql(status)}) "
            f"RETURNING {_DOCUMENT_COLUMNS}"
        )
        rows = _json_query(sql, self._runner)
        return rows[0] if rows else {}

    def set_lineage(self, legacy_document_code: str, superseded_by_document_code: str) -> dict[str, Any] | None:
        sql = (
            f"UPDATE public.seal_engineering_document "
            f"SET superseded_by_document_code = {_sql(superseded_by_document_code)}, "
            f"updated_at = NOW() "
            f"WHERE document_code = {_sql(legacy_document_code)} "
            f"RETURNING {_DOCUMENT_COLUMNS}"
        )
        rows = _json_query(sql, self._runner)
        return rows[0] if rows else None

    def get_document_by_code(self, document_code: str) -> dict[str, Any] | None:
        rows = _json_query(
            f"SELECT {_DOCUMENT_COLUMNS} FROM public.seal_engineering_document "
            f"WHERE document_code = {_sql(document_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def get_document_by_number_and_revision(self, drawing_number: str, revision: str) -> dict[str, Any] | None:
        rows = _json_query(
            f"SELECT {_DOCUMENT_COLUMNS} FROM public.seal_engineering_document "
            f"WHERE document_type = 'DRAWING' AND upper(document_number) = upper({_sql(drawing_number)}) "
            f"AND upper(revision) = upper({_sql(revision)})",
            self._runner,
        )
        return rows[0] if rows else None

    def find_by_checksum(self, sha256_checksum: str) -> dict[str, Any] | None:
        rows = _json_query(
            f"SELECT {_DOCUMENT_COLUMNS} FROM public.seal_engineering_document "
            f"WHERE sha256_checksum = {_sql(sha256_checksum)} LIMIT 1",
            self._runner,
        )
        return rows[0] if rows else None

    def list_documents(
        self,
        *,
        drawing_number: str | None = None,
        seal_code: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = ["document_type = 'DRAWING'"]
        if drawing_number:
            clauses.append(f"upper(document_number) LIKE upper({_sql(f'%{drawing_number}%')})")
        if seal_code:
            clauses.append(f"seal_code = {_sql(seal_code)}")
        if status:
            clauses.append(f"status = {_sql(status)}")
        where = " AND ".join(clauses)
        return _json_query(
            f"SELECT {_DOCUMENT_COLUMNS} FROM public.seal_engineering_document "
            f"WHERE {where} ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}",
            self._runner,
        )

    def list_revisions(self, drawing_number: str) -> list[dict[str, Any]]:
        return _json_query(
            f"SELECT {_DOCUMENT_COLUMNS} FROM public.seal_engineering_document "
            f"WHERE document_type = 'DRAWING' AND upper(document_number) = upper({_sql(drawing_number)}) "
            "ORDER BY created_at DESC",
            self._runner,
        )

    def supersede_previous_revisions(self, drawing_number: str, keep_current_code: str) -> None:
        self._runner.query_scalar(
            "UPDATE public.seal_engineering_document "
            "SET is_current_revision = FALSE, superseded_at = NOW(), status = 'SUPERSEDED' "
            f"WHERE document_type = 'DRAWING' AND upper(document_number) = upper({_sql(drawing_number)}) "
            f"AND document_code <> {_sql(keep_current_code)} AND is_current_revision = TRUE;"
        )

    def update_status(self, document_code: str, status: str, is_current_revision: bool) -> dict[str, Any] | None:
        rows = _json_query(
            "UPDATE public.seal_engineering_document "
            f"SET status = {_sql(status)}, is_current_revision = {'TRUE' if is_current_revision else 'FALSE'}, "
            "updated_at = NOW() "
            f"WHERE document_code = {_sql(document_code)} "
            f"RETURNING {_DOCUMENT_COLUMNS}",
            self._runner,
        )
        return rows[0] if rows else None

    def create_link(
        self,
        *,
        drawing_number: str,
        target_type: str,
        target_code: str,
        source_type: str,
        evidence_method: str,
        confidence_status: str,
        equipment_side: str | None = None,
        document_code: str | None = None,
        raw_reference: str | None = None,
        normalized_reference: str | None = None,
        source_record_id: str | None = None,
        notes: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        doc_code_sql = _sql(document_code) if document_code is not None else "NULL"
        side_sql = _sql(equipment_side) if equipment_side is not None else "NULL"
        sql = (
            "INSERT INTO public.drawing_engineering_link "
            "(document_code, drawing_number, raw_reference, normalized_reference, target_type, "
            "target_code, equipment_side, source_type, source_record_id, evidence_method, confidence_status, notes, created_by) "
            "VALUES ("
            f"{doc_code_sql}, {_sql(drawing_number)}, {_sql(raw_reference)}, {_sql(normalized_reference)}, "
            f"{_sql(target_type)}, {_sql(target_code)}, {side_sql}, {_sql(source_type)}, {_sql(source_record_id)}, "
            f"{_sql(evidence_method)}, {_sql(confidence_status)}, {_sql(notes)}, {_sql(created_by)}) "
            f"RETURNING {_LINK_COLUMNS}"
        )
        rows = _json_query(sql, self._runner)
        return rows[0] if rows else {}

    def list_links_for_document(self, document_code: str) -> list[dict[str, Any]]:
        return _json_query(
            f"SELECT {_LINK_COLUMNS} FROM public.drawing_engineering_link "
            f"WHERE document_code = {_sql(document_code)} ORDER BY created_at ASC",
            self._runner,
        )

    def list_links_for_drawing_number(self, drawing_number: str) -> list[dict[str, Any]]:
        return _json_query(
            f"SELECT {_LINK_COLUMNS} FROM public.drawing_engineering_link "
            f"WHERE upper(drawing_number) = upper({_sql(drawing_number)}) ORDER BY created_at ASC",
            self._runner,
        )

    def list_links_for_target(self, target_type: str, target_code: str) -> list[dict[str, Any]]:
        return _json_query(
            f"SELECT {_LINK_COLUMNS} FROM public.drawing_engineering_link "
            f"WHERE target_type = {_sql(target_type)} AND target_code = {_sql(target_code)} "
            "ORDER BY created_at ASC",
            self._runner,
        )

    def list_drawings_for_target(
        self, target_code: str, target_type: str = "PUMP"
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT "
            "COALESCE(d.document_code, l.document_code) AS document_code, "
            "d.seal_code, "
            "COALESCE(d.document_type, 'DRAWING') AS document_type, "
            "COALESCE(d.document_number, l.drawing_number) AS document_number, "
            "COALESCE(d.title, l.drawing_number || ' Engineering Drawing') AS title, "
            "COALESCE(d.revision, '') AS revision, "
            "d.object_key, "
            "d.sha256_checksum, "
            "d.file_size_bytes, "
            "d.content_type, "
            "d.file_name, "
            "d.uploaded_by, "
            "d.provenance, "
            "d.revision_status, "
            "COALESCE(d.is_current_revision, FALSE) AS is_current_revision, "
            "d.superseded_at, "
            "d.superseded_by_document_code, "
            "d.drawing_generation, "
            "COALESCE(d.status, 'REFERENCE_ONLY') AS status, "
            "d.created_at, "
            "d.updated_at, "
            "l.link_id, "
            "l.target_type, "
            "l.target_code, "
            "l.equipment_side, "
            "l.confidence_status, "
            "l.evidence_method, "
            "l.notes, "
            "l.raw_reference, "
            "l.normalized_reference, "
            "(d.object_key IS NOT NULL AND d.object_key <> '') AS storage_available "
            "FROM public.drawing_engineering_link l "
            "LEFT JOIN public.seal_engineering_document d "
            "ON (l.document_code IS NOT NULL AND d.document_code = l.document_code) "
            "OR (l.document_code IS NULL AND d.document_type = 'DRAWING' AND UPPER(d.document_number) = UPPER(l.drawing_number) AND d.is_current_revision = TRUE) "
            f"WHERE l.target_type = {_sql(target_type)} AND l.target_code = {_sql(target_code)} "
            "ORDER BY l.created_at ASC"
        )
        return _json_query(sql, self._runner)


class InMemoryDrawingRepository:
    """In-memory Drawing Repository for hermetic testing and local simulation."""

    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}
        self.links: list[dict[str, Any]] = []

    def create_document(
        self,
        *,
        document_code: str,
        drawing_number: str,
        title: str,
        revision: str,
        object_key: str,
        sha256_checksum: str,
        file_size_bytes: int,
        content_type: str,
        file_name: str,
        uploaded_by: str | None = None,
        seal_code: str | None = None,
        provenance: str = "MANUAL",
        revision_status: str = "PENDING_REVIEW",
        is_current_revision: bool = False,
        superseded_by_document_code: str | None = None,
        drawing_generation: str | None = None,
        status: str = "APPROVED",
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "document_code": document_code,
            "seal_code": seal_code,
            "document_type": "DRAWING",
            "document_number": drawing_number,
            "title": title,
            "revision": revision,
            "object_key": object_key,
            "sha256_checksum": sha256_checksum,
            "file_size_bytes": file_size_bytes,
            "content_type": content_type,
            "file_name": file_name,
            "uploaded_by": uploaded_by,
            "provenance": provenance,
            "revision_status": revision_status,
            "is_current_revision": is_current_revision,
            "superseded_at": None,
            "superseded_by_document_code": superseded_by_document_code,
            "drawing_generation": drawing_generation,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }
        self.documents[document_code] = doc
        return dict(doc)

    def get_document_by_code(self, document_code: str) -> dict[str, Any] | None:
        doc = self.documents.get(document_code)
        return dict(doc) if doc else None

    def get_document_by_number_and_revision(self, drawing_number: str, revision: str) -> dict[str, Any] | None:
        for doc in self.documents.values():
            if (
                doc.get("document_type") == "DRAWING"
                and str(doc.get("document_number", "")).upper() == drawing_number.upper()
                and str(doc.get("revision", "")).upper() == revision.upper()
            ):
                return dict(doc)
        return None

    def find_by_checksum(self, sha256_checksum: str) -> dict[str, Any] | None:
        for doc in self.documents.values():
            if str(doc.get("sha256_checksum", "")).lower() == sha256_checksum.lower():
                return dict(doc)
        return None

    def list_documents(
        self,
        *,
        drawing_number: str | None = None,
        seal_code: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        results = []
        for doc in self.documents.values():
            if doc.get("document_type") != "DRAWING":
                continue
            if drawing_number and drawing_number.upper() not in str(doc.get("document_number", "")).upper():
                continue
            if seal_code and doc.get("seal_code") != seal_code:
                continue
            if status and doc.get("status") != status:
                continue
            results.append(dict(doc))
        return results[offset : offset + limit]

    def list_revisions(self, drawing_number: str) -> list[dict[str, Any]]:
        return [
            dict(doc)
            for doc in self.documents.values()
            if doc.get("document_type") == "DRAWING"
            and str(doc.get("document_number", "")).upper() == drawing_number.upper()
        ]

    def supersede_previous_revisions(self, drawing_number: str, keep_current_code: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for code, doc in self.documents.items():
            if (
                doc.get("document_type") == "DRAWING"
                and str(doc.get("document_number", "")).upper() == drawing_number.upper()
                and code != keep_current_code
                and doc.get("is_current_revision") is True
            ):
                doc["is_current_revision"] = False
                doc["superseded_at"] = now
                doc["status"] = "SUPERSEDED"

    def update_status(self, document_code: str, status: str, is_current_revision: bool) -> dict[str, Any] | None:
        doc = self.documents.get(document_code)
        if not doc:
            return None
        doc["status"] = status
        doc["is_current_revision"] = is_current_revision
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(doc)

    def set_lineage(self, legacy_document_code: str, superseded_by_document_code: str) -> dict[str, Any] | None:
        doc = self.documents.get(legacy_document_code)
        if not doc:
            return None
        doc["superseded_by_document_code"] = superseded_by_document_code
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(doc)

    def create_link(
        self,
        *,
        drawing_number: str,
        target_type: str,
        target_code: str,
        source_type: str,
        evidence_method: str,
        confidence_status: str,
        equipment_side: str | None = None,
        document_code: str | None = None,
        raw_reference: str | None = None,
        normalized_reference: str | None = None,
        source_record_id: str | None = None,
        notes: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        import uuid

        now = datetime.now(timezone.utc).isoformat()
        link = {
            "link_id": str(uuid.uuid4()),
            "document_code": document_code,
            "drawing_number": drawing_number,
            "raw_reference": raw_reference,
            "normalized_reference": normalized_reference,
            "target_type": target_type,
            "target_code": target_code,
            "equipment_side": equipment_side,
            "source_type": source_type,
            "source_record_id": source_record_id,
            "evidence_method": evidence_method,
            "confidence_status": confidence_status,
            "notes": notes,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
        self.links.append(link)
        return dict(link)

    def list_links_for_document(self, document_code: str) -> list[dict[str, Any]]:
        return [dict(l) for l in self.links if l.get("document_code") == document_code]

    def list_links_for_drawing_number(self, drawing_number: str) -> list[dict[str, Any]]:
        return [dict(l) for l in self.links if str(l.get("drawing_number", "")).upper() == drawing_number.upper()]

    def list_links_for_target(self, target_type: str, target_code: str) -> list[dict[str, Any]]:
        return [
            dict(l)
            for l in self.links
            if l.get("target_type") == target_type and l.get("target_code") == target_code
        ]

    def list_drawings_for_target(
        self, target_code: str, target_type: str = "PUMP"
    ) -> list[dict[str, Any]]:
        links = self.list_links_for_target(target_type, target_code)
        results = []
        for link in links:
            doc_code = link.get("document_code")
            doc = self.documents.get(doc_code) if doc_code else None
            if not doc:
                for d in self.documents.values():
                    if (
                        d.get("document_type") == "DRAWING"
                        and str(d.get("document_number", "")).upper() == str(link.get("drawing_number", "")).upper()
                    ):
                        doc = d
                        break

            row: dict[str, Any] = {}
            if doc:
                row.update(dict(doc))
            else:
                row.update({
                    "document_code": link.get("document_code"),
                    "document_number": link.get("drawing_number"),
                    "title": f"{link.get('drawing_number')} Engineering Drawing",
                    "revision": "",
                    "document_type": "DRAWING",
                    "status": "REFERENCE_ONLY",
                    "drawing_generation": "STANDARD",
                })
            row.update({
                "link_id": link.get("link_id"),
                "target_type": link.get("target_type"),
                "target_code": link.get("target_code"),
                "equipment_side": link.get("equipment_side"),
                "confidence_status": link.get("confidence_status"),
                "evidence_method": link.get("evidence_method"),
                "notes": link.get("notes"),
                "raw_reference": link.get("raw_reference"),
                "normalized_reference": link.get("normalized_reference"),
                "storage_available": bool(row.get("object_key")),
            })
            results.append(row)
        return results


__all__ = [
    "DrawingRepositoryProtocol",
    "DrawingRepository",
    "InMemoryDrawingRepository",
]


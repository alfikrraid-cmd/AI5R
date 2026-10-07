"""Drawing Service for LTSA Mechanical Seal Engineering Drawings.

Orchestrates file validation, cryptographic hashing, conflict detection,
storage staging/promotion, database registration, and audit logging.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from .drawing_file_validator import (
    DrawingFileTooLargeError,
    DrawingSignatureMismatchError,
    DrawingValidationError,
    InvalidDrawingExtensionError,
    validate_drawing_file,
)
from .drawing_reference_normalizer import (
    normalize_reference,
    parse_reference_components,
)
from .drawing_repository import (
    DrawingRepositoryProtocol,
    InMemoryDrawingRepository,
)
from .minio_storage_service import (
    InMemoryStorageService,
    StorageServiceProtocol,
    generate_drawing_object_key,
    generate_staged_object_key,
)

logger = logging.getLogger("ltsa.drawing_service")


class DrawingConflictError(ValueError):
    """Raised when an uploaded revision conflicts with an existing different binary (HTTP 409)."""


class DrawingNotFoundError(KeyError):
    """Raised when a requested drawing document does not exist (HTTP 404)."""


class DrawingService:
    """Canonical service for managing engineering drawings, revisions, and linkages."""

    def __init__(
        self,
        repository: DrawingRepositoryProtocol | None = None,
        storage_service: StorageServiceProtocol | None = None,
        change_history_repository: Any | None = None,
    ) -> None:
        self.repository = repository or InMemoryDrawingRepository()
        self.storage = storage_service or InMemoryStorageService()
        self.change_history = change_history_repository

    def register_drawing(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        drawing_number: str,
        title: str,
        revision: str | None = None,
        uploaded_by: str | None = None,
        seal_code: str | None = None,
        asset_code: str | None = None,
        provenance: str = "MANUAL",
        is_revision_upload: bool = False,
    ) -> dict[str, Any]:
        """Validates and registers an engineering drawing binary and metadata."""
        # 1. Validation (extension, size, magic signature)
        validated = validate_drawing_file(file_bytes, filename)
        clean_ext = str(validated["clean_extension"])
        content_type = str(validated["content_type"])
        file_size_bytes = int(validated["file_size_bytes"])

        # 2. SHA-256 calculation
        sha256_hex = hashlib.sha256(file_bytes).hexdigest()

        # 3. Normalized drawing identity
        raw_drawing_number = drawing_number.strip()
        norm_drawing_number = normalize_reference(raw_drawing_number)
        norm_revision = (revision.strip().upper() if revision else "UNKNOWN") or "UNKNOWN"

        # 4. Conflict & Deduplication Check
        existing_rev = self.repository.get_document_by_number_and_revision(
            norm_drawing_number, norm_revision
        )

        if existing_rev is not None:
            existing_sha = str(existing_rev.get("sha256_checksum", "")).lower()
            if existing_sha == sha256_hex.lower():
                # Idempotent deduplication: exact same binary on same revision
                logger.info(
                    "Idempotent upload for drawing %s Rev %s (SHA %s)",
                    norm_drawing_number,
                    norm_revision,
                    sha256_hex[:8],
                )
                return existing_rev
            else:
                # Same drawing number + same revision + DIFFERENT binary -> 409 CONFLICT
                raise DrawingConflictError(
                    f"Conflict: Drawing {norm_drawing_number} revision {norm_revision} already exists "
                    f"with different content (existing SHA: {existing_sha[:8]}, new SHA: {sha256_hex[:8]}). "
                    "Cannot overwrite an existing engineering revision."
                )

        # 5. Staging object in storage
        staged_key = generate_staged_object_key(sha256_hex, clean_ext)
        final_key = generate_drawing_object_key(
            norm_drawing_number, norm_revision, sha256_hex, clean_ext
        )

        self.storage.put_staged_object(staged_key, file_bytes, content_type)
        if not self.storage.verify_object(staged_key, sha256_hex):
            raise DrawingValidationError("Storage verification failed: checksum mismatch after upload")

        self.storage.register_promoted_object(staged_key, final_key)

        # 6. Database Registration with recoverable quarantine handling
        document_code = f"DOC-DWG-{uuid.uuid4().hex[:12].upper()}"

        # Invariant: UNKNOWN revision NEVER becomes CURRENT automatically!
        if norm_revision == "UNKNOWN":
            revision_status = "PENDING_REVIEW"
            is_current = False
            doc_status = "PENDING_REVIEW"
        else:
            revision_status = "APPROVED"
            is_current = True
            doc_status = "APPROVED"

        try:
            created = self.repository.create_document(
                document_code=document_code,
                drawing_number=norm_drawing_number,
                title=title.strip(),
                revision=norm_revision,
                object_key=final_key,
                sha256_checksum=sha256_hex,
                file_size_bytes=file_size_bytes,
                content_type=content_type,
                file_name=filename,
                uploaded_by=uploaded_by,
                seal_code=seal_code,
                provenance=provenance,
                revision_status=revision_status,
                is_current_revision=is_current,
                status=doc_status,
            )

            # Enforce at-most-one current revision if this one became CURRENT
            if is_current:
                self.repository.supersede_previous_revisions(norm_drawing_number, document_code)

            # Establish explicit linkage if requested
            if seal_code:
                self.repository.create_link(
                    document_code=document_code,
                    drawing_number=norm_drawing_number,
                    raw_reference=raw_drawing_number,
                    normalized_reference=norm_drawing_number,
                    target_type="SEAL",
                    target_code=seal_code,
                    source_type="ENGINEERING_DOCUMENT",
                    evidence_method="EXPLICIT_METADATA",
                    confidence_status="CONFIRMED",
                    created_by=uploaded_by,
                )

            if asset_code:
                self.repository.create_link(
                    document_code=document_code,
                    drawing_number=norm_drawing_number,
                    raw_reference=raw_drawing_number,
                    normalized_reference=norm_drawing_number,
                    target_type="PUMP",
                    target_code=asset_code,
                    source_type="ENGINEERING_DOCUMENT",
                    evidence_method="EXPLICIT_METADATA",
                    confidence_status="CONFIRMED",
                    created_by=uploaded_by,
                )

        except Exception as exc:
            # Recoverable staging: quarantine the file rather than destroying it!
            logger.error("DB registration failed for %s. Quarantining storage object: %s", document_code, exc)
            self.storage.quarantine_object(final_key, reason=f"DB_REGISTRATION_FAILED: {exc}")
            raise RuntimeError(f"Database registration failed; file quarantined for recovery: {exc}") from exc

        # 7. Audit Logging
        if self.change_history is not None and uploaded_by is not None:
            try:
                action = "REVISION_UPLOAD" if is_revision_upload else "DRAWING_UPLOAD"
                self.change_history.append(
                    entity_type="DRAWING",
                    entity_id=document_code,
                    field_name=action,
                    old_value=None,
                    new_value=f"Number={norm_drawing_number}, Rev={norm_revision}, SHA={sha256_hex[:8]}",
                    changed_by=str(uploaded_by),
                    reason=f"{action}: {title}",
                    source_reference=final_key,
                )
            except Exception as audit_err:
                logger.warning("Audit log write failed for drawing upload: %s", audit_err)

        return created

    def get_drawing(self, document_code: str) -> dict[str, Any]:
        """Retrieves drawing document metadata along with revisions and links."""
        doc = self.repository.get_document_by_code(document_code)
        if doc is None:
            raise DrawingNotFoundError(f"Drawing document {document_code} not found")

        drawing_number = doc.get("document_number", "")
        revisions = self.repository.list_revisions(drawing_number)
        links = self.repository.list_links_for_document(document_code)
        object_key = doc.get("object_key", "")
        storage_available = self.storage.object_exists(object_key) if object_key else False

        return {
            **doc,
            "revisions": revisions,
            "links": links,
            "storage_available": storage_available,
        }

    def get_drawing_content(self, document_code: str) -> tuple[bytes, str, str]:
        """Retrieves binary content, MIME type, and safe download filename for a drawing."""
        doc = self.repository.get_document_by_code(document_code)
        if doc is None:
            raise DrawingNotFoundError(f"Drawing document {document_code} not found")

        object_key = doc.get("object_key")
        if not object_key or not self.storage.object_exists(object_key):
            raise DrawingNotFoundError(f"Binary file for drawing {document_code} not found in storage")

        content_bytes = self.storage.get_object_bytes(object_key)
        content_type = doc.get("content_type") or "application/octet-stream"
        filename = doc.get("file_name") or f"{doc.get('document_number')}_rev{doc.get('revision')}.pdf"

        return content_bytes, content_type, filename

    def add_reference_only_link(
        self,
        *,
        drawing_number: str,
        target_type: str,
        target_code: str,
        source_type: str,
        source_record_id: str | None = None,
        created_by: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Registers a first-class REFERENCE_ONLY association without requiring a physical file."""
        norm_dwg = normalize_reference(drawing_number)
        return self.repository.create_link(
            document_code=None,  # Nullable for reference-only
            drawing_number=norm_dwg,
            raw_reference=drawing_number,
            normalized_reference=norm_dwg,
            target_type=target_type,
            target_code=target_code,
            source_type=source_type,
            source_record_id=source_record_id,
            evidence_method="SOURCE_REFERENCE",
            confidence_status="REFERENCE_ONLY",
            notes=notes,
            created_by=created_by,
        )

    def link_drawing(
        self,
        *,
        document_code: str,
        target_type: str,
        target_code: str,
        evidence_method: str = "MANUAL_VERIFICATION",
        created_by: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Links an existing authoritative drawing document to an asset or seal."""
        doc = self.repository.get_document_by_code(document_code)
        if doc is None:
            raise DrawingNotFoundError(f"Drawing document {document_code} not found")

        drawing_number = doc.get("document_number", "")
        link = self.repository.create_link(
            document_code=document_code,
            drawing_number=drawing_number,
            raw_reference=drawing_number,
            normalized_reference=normalize_reference(drawing_number),
            target_type=target_type,
            target_code=target_code,
            source_type="MANUAL_LINK",
            evidence_method=evidence_method,
            confidence_status="CONFIRMED",
            notes=notes,
            created_by=created_by,
        )

        if self.change_history is not None and created_by is not None:
            try:
                self.change_history.append(
                    entity_type="DRAWING",
                    entity_id=document_code,
                    field_name="DRAWING_LINK",
                    old_value=None,
                    new_value=f"{target_type}:{target_code}",
                    changed_by=str(created_by),
                    reason=f"Linked drawing {drawing_number} to {target_type} {target_code}",
                )
            except Exception as audit_err:
                logger.warning("Audit log write failed for drawing link: %s", audit_err)

        return link


__all__ = [
    "DrawingConflictError",
    "DrawingNotFoundError",
    "DrawingService",
]


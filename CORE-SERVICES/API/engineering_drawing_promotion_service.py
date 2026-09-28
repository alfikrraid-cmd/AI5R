"""MWO-LTSA-DRAWING-INPUT-R5D.1 -- Engineering Drawing atomic promotion
CORE: turns a REVIEWED document_field_extraction ENGINEERING_DRAWING_
CANDIDATE row into real engineering_drawing/_revision/_revision_artifact/
_attribute/_bom_line/_link canonical rows, atomically, exactly once per
candidate, using ONLY the reviewed_fields authority R5C/R5C.1 already
established.

RAW AUTHORITY (extracted_fields) is read in exactly one situation: an
ACCEPTED identity/revision/attribute/BOM decision carries no value of its
own in reviewed_fields (R5C's own apply_*_review() stores only
{"review_status": "ACCEPTED"} for ACCEPT -- the value IS the original
extracted candidate). Reading extracted_fields to recover THAT confirmed
value is not "inferring a canonical value from raw extraction" (which
R5C.1/R5D0 both prohibit) -- it is retrieving the exact fact a human
already reviewed and accepted. A CORRECTED decision never needs this --
its replacement value is already inside reviewed_fields. A REJECTED or
absent (deferred) decision never promotes anything for that fact.
References are the one exception with no ACCEPT path at all: R5B's own
ReferenceCandidate never carries a target_type/target_code/
relationship_type (Drawing-R5B Section 8's own "R5B never resolves or
links these" rule) -- only an explicit CORRECT with a caller-supplied
{target_type, target_code, relationship_type} dict can ever produce a
promotable link. An ACCEPTED reference is therefore never linked (there
is nothing accept-able for a link identity).

TRANSACTION MODEL: this service manages its own real psycopg2 connection
(autocommit=False), matching this MWO's own Section 2 Option B ("implement
promotion SQL in the R5D service using one shared connection/transaction")
rather than calling any existing repository/service method -- every other
Drawing repository/service in this codebase (engineering_drawing_
repository.py, engineering_drawing_review_service.py, R5B's staging
service) achieves atomicity via DatabaseRunner.query_scalar()/
execute_script(), each of which opens AND CLOSES its own connection per
call (confirmed by reading ltsa_pump_inventory_db_upsert.py's own
DatabaseRunner._direct_connect()/query_scalar()/execute_script() --there
is no shared-transaction primitive across separate calls). Since Drawing
promotion has variable cardinality (N attributes, N BOM lines, N links per
candidate), a single CTE statement covering all of it (the pattern R4/R5B/
R5C/historical_pm_cmon_promotion_service.py all use) is impractical --
this service instead opens ONE real connection, disables autocommit, and
issues multiple plain parameterized statements against ONE shared cursor,
committing only once everything succeeds and rolling back on any failure.
No existing shared file (ltsa_pump_inventory_db_upsert.py included) is
modified to make this possible.

CANONICAL WRITES happen ONLY here (never in R5B/R5C) and ONLY once per
candidate: engineering_drawing_promotion.candidate_id is UNIQUE (migration
040) and is checked FIRST, before any other write, giving retry-safe
idempotency without relying on check-then-insert alone -- combined with
deterministic, content-derived codes for every created row (see
_deterministic_code below) so that two independent promotion attempts for
the same real-world identity (same candidate retried, OR two different
candidates that resolve to the same drawing/revision) always compute the
SAME code and safely converge via INSERT ... ON CONFLICT DO NOTHING plus a
fallback SELECT ... FOR UPDATE, rather than a blind check-then-insert race.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .engineering_drawing_review_contract import (
    ARTIFACT_CLASSES,
    REVIEW_SCHEMA_VERSION,
    STATUS_REJECTED,
    STATUS_REVIEWED,
    STATUS_SAVED,
    is_promotion_eligible,
)

# ---- bounded exceptions (Section 23) -- one per distinct promotion rule ----


class CandidateNotFound(Exception):
    """candidate_id does not exist, or is not an ENGINEERING_DRAWING_CANDIDATE."""


class CandidateNotEligible(Exception):
    """status != REVIEWED, or is_promotion_eligible(reviewed_fields) is False."""


class CandidateRejected(Exception):
    """candidate status is REJECTED -- never promotable."""


class InvalidReviewPayload(Exception):
    """reviewed_fields is missing review_schema_version (UNVERSIONED_REVIEW),
    malformed, or resolves to a value that violates a NOT NULL canonical
    column (e.g. title has no promotable ACCEPT/CORRECT value)."""


class DrawingMatchRequiresReview(Exception):
    """drawing_number matches an existing drawing under an unresolved/
    absent manufacturer -- ambiguous, never auto-merged, never silently
    turned into a second drawing either."""


class RevisionMatchRequiresReview(Exception):
    """Reserved for a revision-matching ambiguity; no condition in this
    implementation currently raises it (revision matching is exact-value
    only, per R5D0's own conservative model) -- kept for the bounded error
    vocabulary Section 23 requires and any future stricter revision policy."""


class CanonicalConflict(Exception):
    """A deterministic code resolved to an existing row whose identity
    does not match what this candidate expected (a genuine hash collision,
    or a manufacturer/drawing_number identity conflict this candidate
    cannot silently resolve)."""


class ReferenceNotFound(Exception):
    """An explicitly reviewed reference's target_code does not exist in
    its own target_type's canonical authority table."""


class ScopeDenied(Exception):
    """The promoting actor's Area/MA scope does not cover any area this
    drawing resolves to (or the drawing has no determinable ASSET area at
    all) -- fails closed, exactly like R4's own is_drawing_in_scope()."""


class AlreadyPromoted(Exception):
    """candidate_id already has a row in engineering_drawing_promotion (or
    status is already SAVED) -- idempotent replay. Carries the prior
    promotion's own deterministic result on .result so a caller can still
    read it without a second lookup."""

    def __init__(self, message: str, result: dict[str, Any]):
        super().__init__(message)
        self.result = result


class PromotionConcurrencyConflict(Exception):
    """A lower-level DB conflict could not be resolved by this service's
    own deterministic-code + ON CONFLICT DO NOTHING + fallback-SELECT
    strategy (e.g. a same-candidate race that somehow bypassed the
    candidate-row FOR UPDATE lock) -- never silently retried automatically."""


# ---- constants ----

_REVIEWABLE_ARTIFACT_STATUSES = ("ACCEPTED", "CORRECTED")
_PROMOTABLE_STATUSES = ("ACCEPTED", "CORRECTED")

# Mirrors engineering_drawing_repository.py's own private _TARGET_AUTHORITY
# exactly (ASSET/SEAL/COMPONENT -> table/column) -- duplicated here rather
# than imported because that repository's own connection/transaction
# cannot be shared with this service's single-connection promotion
# transaction (see module docstring); kept in sync manually if the R4
# repository's own map ever changes.
_TARGET_AUTHORITY = {
    "ASSET": ("asset_registry", "asset_code"),
    "SEAL": ("seal_registry", "seal_code"),
    "COMPONENT": ("internal_component_master", "component_id"),
}
_ALLOWED_RELATIONSHIP_TYPES = frozenset({"APPLIES_TO", "DEPICTS", "COMPONENT_OF"})

_DETECTED_DOCUMENT_TYPE = "ENGINEERING_DRAWING_CANDIDATE"


def _deterministic_code(prefix: str, *parts: str) -> str:
    """Content-derived, retry-safe code -- the SAME inputs always produce
    the SAME code, letting two independent promotion attempts (a retry of
    the same candidate, or two different candidates resolving to the same
    real-world drawing/revision) converge on one row via
    INSERT ... ON CONFLICT DO NOTHING + a fallback SELECT, rather than a
    plain random UUID (R4's own `_new_code()` convention, unchanged and
    still used for direct/manual R4 API creation -- this is a SEPARATE,
    narrower code path used only by this service's own atomic promotion)."""
    seed = "\x1f".join(parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}-{digest}"


def _resolve_identity_value(reviewed_identity: dict, extracted_identity: dict, field_name: str) -> str | None:
    decision = reviewed_identity.get(field_name)
    if not decision:
        return None
    status = decision.get("review_status")
    if status == "REJECTED":
        return None
    if status == "CORRECTED":
        return decision.get("value")
    if status == "ACCEPTED":
        return (extracted_identity.get(field_name) or {}).get("raw_value")
    return None


def _resolve_revision_value(reviewed_revision: dict | None, extracted_revision: dict) -> tuple[str | None, str | None]:
    if not reviewed_revision:
        return None, None
    status = reviewed_revision.get("review_status")
    if status == "REJECTED":
        return None, None
    if status == "CORRECTED":
        return reviewed_revision.get("revision"), reviewed_revision.get("revision_date")
    if status == "ACCEPTED":
        return extracted_revision.get("revision"), extracted_revision.get("revision_date")
    return None, None


class EngineeringDrawingPromotionService:
    def __init__(self, config) -> None:
        self._config = config

    def _connect(self):
        import psycopg2

        conn = psycopg2.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            dbname=self._config.database,
        )
        conn.autocommit = False
        return conn

    # ================= orchestration =================

    def promote_candidate(self, candidate_id: str, *, promoted_by: str, actor_scope: frozenset[str] | None = None) -> dict:
        from psycopg2.extras import RealDictCursor

        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                candidate = self._lock_candidate(cur, candidate_id)

                existing = self._find_existing_promotion(cur, candidate_id)
                if existing is not None or candidate["status"] == STATUS_SAVED:
                    conn.rollback()
                    raise AlreadyPromoted(candidate_id, self._already_promoted_result(candidate_id, existing))

                if candidate["status"] == STATUS_REJECTED:
                    raise CandidateRejected(candidate_id)
                if candidate["status"] != STATUS_REVIEWED:
                    raise CandidateNotEligible(f"{candidate_id} has status {candidate['status']!r}, expected REVIEWED")

                reviewed = candidate["reviewed_fields"] or {}
                extracted = candidate["extracted_fields"] or {}

                if reviewed.get("review_schema_version") != REVIEW_SCHEMA_VERSION:
                    raise InvalidReviewPayload(
                        f"{candidate_id} reviewed_fields is UNVERSIONED_REVIEW "
                        f"(expected review_schema_version={REVIEW_SCHEMA_VERSION!r})"
                    )
                if not is_promotion_eligible(reviewed):
                    raise CandidateNotEligible(f"{candidate_id} is not promotion eligible (identity/artifact unresolved)")

                self._validate_knowledge_source(cur, candidate["source_document_id"])

                reviewed_identity = reviewed.get("drawing_identity") or {}
                extracted_identity = extracted.get("drawing_identity") or {}
                title_value = _resolve_identity_value(reviewed_identity, extracted_identity, "title")
                if not title_value:
                    raise InvalidReviewPayload(f"{candidate_id} has no promotable title value (NOT NULL canonical column)")
                manufacturer_value = _resolve_identity_value(reviewed_identity, extracted_identity, "manufacturer")
                drawing_number_value = _resolve_identity_value(reviewed_identity, extracted_identity, "drawing_number")
                drawing_type_value = _resolve_identity_value(reviewed_identity, extracted_identity, "drawing_type")

                drawing_code, drawing_match, drawing_created, drawing_warning = self._resolve_drawing(
                    cur, candidate_id, manufacturer_value, drawing_number_value, title_value, drawing_type_value, promoted_by,
                )

                reviewed_revision = reviewed.get("revision_candidate")
                extracted_revision = extracted.get("revision_candidate") or {}
                revision_value, revision_date_value = _resolve_revision_value(reviewed_revision, extracted_revision)
                revision_code, revision_match, revision_created = self._resolve_revision(
                    cur, candidate_id, drawing_code, revision_value, revision_date_value, promoted_by,
                )

                resolved_references, warnings = self._resolve_references(
                    reviewed.get("references") or {}, extracted.get("references") or [],
                )
                if drawing_warning is not None:
                    warnings.append(drawing_warning)
                self._validate_references(cur, resolved_references)
                self._enforce_scope(cur, drawing_code, drawing_created, resolved_references, actor_scope)

                artifact = reviewed.get("artifact") or {}
                artifact_code = self._resolve_artifact(cur, candidate_id, revision_code, artifact, promoted_by)

                attribute_codes = self._promote_attributes(
                    cur, candidate_id, revision_code, artifact_code,
                    reviewed.get("attributes") or {}, extracted.get("attributes") or [], promoted_by,
                )
                bom_line_codes = self._promote_bom_lines(
                    cur, candidate_id, revision_code,
                    reviewed.get("bom_candidates") or {}, extracted.get("bom_candidates") or [], promoted_by,
                )
                link_codes = self._insert_links(cur, candidate_id, drawing_code, resolved_references, promoted_by)

                if drawing_created and revision_created:
                    self._set_current_revision(cur, drawing_code, revision_code, promoted_by)

                self._insert_promotion_row(cur, candidate_id, drawing_code, revision_code, artifact_code, promoted_by)
                self._transition_candidate_saved(cur, candidate_id, promoted_by)

            conn.commit()
            return {
                "candidate_id": candidate_id,
                "promotion_status": "PROMOTED",
                "drawing_code": drawing_code,
                "drawing_match": drawing_match,
                "revision_code": revision_code,
                "revision_match": revision_match,
                "artifact_codes": [artifact_code],
                "attribute_codes": attribute_codes,
                "bom_line_codes": bom_line_codes,
                "link_codes": link_codes,
                "warnings": warnings,
                "conflicts": [],
                "idempotent_replay": False,
            }
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def promotion_status(self, candidate_id: str) -> dict | None:
        """Read-only convenience lookup (its own short-lived connection,
        no lock) -- never used internally by promote_candidate()."""
        from psycopg2.extras import RealDictCursor

        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT promotion_code, candidate_id, drawing_code, revision_code, artifact_code, "
                    "promoted_by, promoted_at FROM engineering_drawing_promotion WHERE candidate_id = %s",
                    (candidate_id,),
                )
                row = cur.fetchone()
            conn.rollback()
            return dict(row) if row else None
        finally:
            conn.close()

    # ================= steps =================

    def _lock_candidate(self, cur, candidate_id: str) -> dict:
        cur.execute(
            "SELECT document_field_extraction_id, source_document_id, detected_document_type, status, "
            "extracted_fields, reviewed_fields, updated_at "
            "FROM document_field_extraction WHERE document_field_extraction_id = %s "
            "AND detected_document_type = %s FOR UPDATE",
            (candidate_id, _DETECTED_DOCUMENT_TYPE),
        )
        row = cur.fetchone()
        if row is None:
            raise CandidateNotFound(candidate_id)
        return dict(row)

    def _find_existing_promotion(self, cur, candidate_id: str) -> dict | None:
        cur.execute(
            "SELECT promotion_code, drawing_code, revision_code, artifact_code "
            "FROM engineering_drawing_promotion WHERE candidate_id = %s",
            (candidate_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def _already_promoted_result(self, candidate_id: str, existing: dict | None) -> dict:
        if existing is None:
            # status is SAVED but no promotion row exists (should be
            # unreachable given this service is the only writer of either
            # fact together) -- reported honestly rather than fabricated.
            return {
                "candidate_id": candidate_id, "promotion_status": "ALREADY_PROMOTED", "drawing_code": None,
                "drawing_match": None, "revision_code": None, "revision_match": None, "artifact_codes": [],
                "attribute_codes": [], "bom_line_codes": [], "link_codes": [],
                "warnings": ["candidate is SAVED but no engineering_drawing_promotion row was found"],
                "conflicts": [], "idempotent_replay": True,
            }
        return {
            "candidate_id": candidate_id, "promotion_status": "ALREADY_PROMOTED",
            "drawing_code": existing["drawing_code"], "drawing_match": "ALREADY_PROMOTED",
            "revision_code": existing["revision_code"], "revision_match": "ALREADY_PROMOTED",
            "artifact_codes": [existing["artifact_code"]], "attribute_codes": [], "bom_line_codes": [],
            "link_codes": [], "warnings": [], "conflicts": [], "idempotent_replay": True,
        }

    def _validate_knowledge_source(self, cur, knowledge_source_id: str) -> None:
        cur.execute("SELECT 1 FROM knowledge_source_registry WHERE knowledge_source_id = %s", (knowledge_source_id,))
        if cur.fetchone() is None:
            raise InvalidReviewPayload(f"knowledge_source_id {knowledge_source_id!r} does not exist")

    # ---- drawing ----

    def _resolve_drawing(
        self, cur, candidate_id: str, manufacturer: str | None, drawing_number: str | None,
        title: str, drawing_type: str | None, promoted_by: str,
    ) -> tuple[str, str, bool, dict | None]:
        if manufacturer is not None and drawing_number is not None:
            cur.execute(
                "SELECT drawing_code, manufacturer, drawing_number, title FROM engineering_drawing "
                "WHERE upper(btrim(manufacturer)) = upper(btrim(%s)) AND drawing_number = %s FOR UPDATE",
                (manufacturer, drawing_number),
            )
            existing = cur.fetchone()
            if existing is not None:
                warning = None
                if existing["title"] != title:
                    # Section 18/20: existing canonical field always wins;
                    # a differing reviewed title is surfaced, never
                    # silently overwritten.
                    warning = {
                        "field": "title", "message": "reviewed title differs from existing canonical drawing.title; existing value was kept",
                    }
                return existing["drawing_code"], "EXACT_MATCH", False, warning

            code = _deterministic_code("ENGDRW", "identity", manufacturer.strip().upper(), drawing_number)
            drawing_code, match, created = self._insert_or_fetch_drawing(cur, code, manufacturer, drawing_number, title, drawing_type, promoted_by)
            return drawing_code, match, created, None

        if drawing_number is not None and manufacturer is None:
            # Section 5/R5D0: drawing_number alone matching an existing
            # row (of ANY manufacturer) is ambiguous -- we cannot confirm
            # or rule out identity without a resolved manufacturer.
            cur.execute("SELECT 1 FROM engineering_drawing WHERE drawing_number = %s", (drawing_number,))
            if cur.fetchone() is not None:
                raise DrawingMatchRequiresReview(
                    f"drawing_number {drawing_number!r} matches an existing drawing but manufacturer is unresolved"
                )
            code = _deterministic_code("ENGDRW", "candidate", candidate_id)
            drawing_code, match, created = self._insert_or_fetch_drawing(cur, code, manufacturer, drawing_number, title, drawing_type, promoted_by)
            return drawing_code, match, created, None

        # drawing_number is None (Section 7): never search by title, never
        # ambiguity-checked -- always its own deterministic NEW_DRAWING.
        code = _deterministic_code("ENGDRW", "candidate", candidate_id)
        drawing_code, match, created = self._insert_or_fetch_drawing(cur, code, manufacturer, drawing_number, title, drawing_type, promoted_by)
        return drawing_code, match, created, None

    def _insert_or_fetch_drawing(
        self, cur, code: str, manufacturer: str | None, drawing_number: str | None,
        title: str, drawing_type: str | None, promoted_by: str,
    ) -> tuple[str, str, bool]:
        # R5D.1C fix: engineering_drawing carries TWO independent unique
        # constraints -- the drawing_code PK and
        # idx_engineering_drawing_identity_unique (migration 040) on
        # (upper(btrim(manufacturer)), drawing_number). An
        # ON CONFLICT (drawing_code) DO NOTHING only suppressed a conflict
        # on the PK arbiter; two concurrent candidates with identical
        # identity (same identity-derived drawing_code AND the same
        # manufacturer/drawing_number) could raise an UNSUPPRESSED
        # UniqueViolation on the OTHER constraint instead. An unqualified
        # ON CONFLICT DO NOTHING absorbs a conflict on ANY unique/
        # exclusion constraint for this INSERT -- the fallback SELECT
        # below (with its own identity-match validation) remains the sole
        # authority for what gets reused, unchanged.
        cur.execute(
            "INSERT INTO engineering_drawing (drawing_code, drawing_number, title, manufacturer, drawing_type, created_by, updated_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING "
            "RETURNING drawing_code",
            (code, drawing_number, title, manufacturer, drawing_type, promoted_by, promoted_by),
        )
        row = cur.fetchone()
        if row is not None:
            return code, "NEW_DRAWING", True

        cur.execute(
            "SELECT drawing_code, manufacturer, drawing_number FROM engineering_drawing WHERE drawing_code = %s FOR UPDATE",
            (code,),
        )
        existing = cur.fetchone()
        existing_manufacturer_norm = (existing["manufacturer"] or "").strip().upper() if existing else None
        candidate_manufacturer_norm = (manufacturer or "").strip().upper() if manufacturer else None
        if existing is None or existing_manufacturer_norm != candidate_manufacturer_norm or existing["drawing_number"] != drawing_number:
            raise CanonicalConflict(f"deterministic drawing_code {code} collided with a non-equivalent existing row")
        return code, "NEW_DRAWING", False

    # ---- revision ----

    def _resolve_revision(
        self, cur, candidate_id: str, drawing_code: str, revision: str | None, revision_date: str | None, promoted_by: str,
    ) -> tuple[str, str, bool]:
        if revision is not None:
            cur.execute(
                "SELECT revision_code FROM engineering_drawing_revision WHERE drawing_code = %s AND revision = %s FOR UPDATE",
                (drawing_code, revision),
            )
            existing = cur.fetchone()
            if existing is not None:
                return existing["revision_code"], "EXACT_MATCH", False
            code = _deterministic_code("ENGDRWREV", "identity", drawing_code, revision)
        else:
            code = _deterministic_code("ENGDRWREV", "candidate", candidate_id)

        # R5D.1C fix: same reasoning as _insert_or_fetch_drawing() above --
        # engineering_drawing_revision also carries a second unique index
        # (idx_engineering_drawing_revision_identity_unique, migration
        # 040) beyond its own revision_code PK; an unqualified
        # ON CONFLICT DO NOTHING is required here for the same reason.
        cur.execute(
            "INSERT INTO engineering_drawing_revision (revision_code, drawing_code, revision, revision_date, created_by, updated_by) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING revision_code",
            (code, drawing_code, revision, revision_date, promoted_by, promoted_by),
        )
        row = cur.fetchone()
        if row is not None:
            return code, "NEW_REVISION", True

        cur.execute(
            "SELECT revision_code, drawing_code, revision FROM engineering_drawing_revision WHERE revision_code = %s FOR UPDATE",
            (code,),
        )
        existing = cur.fetchone()
        if existing is None or existing["drawing_code"] != drawing_code or existing["revision"] != revision:
            raise CanonicalConflict(f"deterministic revision_code {code} collided with a non-equivalent existing row")
        return code, "NEW_REVISION", False

    def _set_current_revision(self, cur, drawing_code: str, revision_code: str, promoted_by: str) -> None:
        cur.execute(
            "UPDATE engineering_drawing SET current_revision_code = %s, updated_by = %s, updated_at = NOW() "
            "WHERE drawing_code = %s AND current_revision_code IS NULL",
            (revision_code, promoted_by, drawing_code),
        )

    # ---- artifact ----

    def _resolve_artifact(self, cur, candidate_id: str, revision_code: str, artifact: dict, promoted_by: str) -> str:
        status = artifact.get("review_status")
        value = artifact.get("value")
        if status not in _REVIEWABLE_ARTIFACT_STATUSES or value not in ARTIFACT_CLASSES:
            raise InvalidReviewPayload(f"{candidate_id} artifact review is not resolved ({status!r}/{value!r})")
        knowledge_source_id = artifact.get("knowledge_source_id")

        code = _deterministic_code("ENGART", "candidate", candidate_id)
        cur.execute(
            "INSERT INTO engineering_drawing_revision_artifact "
            "(artifact_code, revision_code, knowledge_source_id, artifact_class, created_by, updated_by) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (artifact_code) DO NOTHING RETURNING artifact_code",
            (code, revision_code, knowledge_source_id, value, promoted_by, promoted_by),
        )
        row = cur.fetchone()
        if row is not None:
            return code

        cur.execute(
            "SELECT artifact_code, revision_code, artifact_class FROM engineering_drawing_revision_artifact "
            "WHERE artifact_code = %s FOR UPDATE",
            (code,),
        )
        existing = cur.fetchone()
        if existing is None or existing["revision_code"] != revision_code or existing["artifact_class"] != value:
            raise CanonicalConflict(f"deterministic artifact_code {code} collided with a non-equivalent existing row")
        return code

    # ---- attributes ----

    def _promote_attributes(
        self, cur, candidate_id: str, revision_code: str, artifact_code: str,
        reviewed_attributes: dict, extracted_attributes: list, promoted_by: str,
    ) -> list[str]:
        codes: list[str] = []
        for index_str, decision in reviewed_attributes.items():
            status = decision.get("review_status")
            if status not in _PROMOTABLE_STATUSES:
                continue
            index = int(index_str)
            raw_candidate = extracted_attributes[index] if index < len(extracted_attributes) else {}
            if status == "CORRECTED":
                value = decision.get("value") or {}
                concept = value.get("concept", raw_candidate.get("concept"))
                source_label = value.get("source_label", raw_candidate.get("source_label"))
                value_numeric = value.get("value_numeric", raw_candidate.get("value_numeric"))
                value_text = value.get("value_text", raw_candidate.get("value_text"))
                unit = value.get("unit", raw_candidate.get("unit"))
                source_location = value.get("source_location", raw_candidate.get("source_location"))
            else:  # ACCEPTED
                concept = raw_candidate.get("concept")
                source_label = raw_candidate.get("source_label")
                value_numeric = raw_candidate.get("value_numeric")
                value_text = raw_candidate.get("value_text")
                unit = raw_candidate.get("unit")
                source_location = raw_candidate.get("source_location")

            if not concept or (value_numeric is None and value_text is None):
                raise InvalidReviewPayload(f"{candidate_id} attribute[{index}] has no promotable concept/value")

            code = _deterministic_code("ENGATTR", "candidate", candidate_id, "index", str(index))
            cur.execute(
                "INSERT INTO engineering_drawing_attribute "
                "(attribute_code, revision_code, source_artifact_code, attribute_concept, source_label, "
                "value_numeric, value_text, unit, source_location, verification_status, reviewed_by, reviewed_at, created_by, updated_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'VERIFIED', %s, NOW(), %s, %s) "
                "ON CONFLICT (attribute_code) DO NOTHING RETURNING attribute_code",
                (
                    code, revision_code, artifact_code, concept, source_label, value_numeric, value_text,
                    unit, source_location, promoted_by, promoted_by, promoted_by,
                ),
            )
            row = cur.fetchone()
            codes.append(code if row is not None else code)
        return codes

    # ---- BOM ----

    def _promote_bom_lines(
        self, cur, candidate_id: str, revision_code: str,
        reviewed_bom: dict, extracted_bom: list, promoted_by: str,
    ) -> list[str]:
        codes: list[str] = []
        for index_str, decision in reviewed_bom.items():
            status = decision.get("review_status")
            if status not in _PROMOTABLE_STATUSES:
                continue
            index = int(index_str)
            raw_candidate = extracted_bom[index] if index < len(extracted_bom) else {}
            component_id = None
            if status == "CORRECTED":
                value = decision.get("value") or {}
                item_position = value.get("item_position", raw_candidate.get("item_position"))
                description = value.get("component_description", raw_candidate.get("description"))
                quantity = value.get("quantity")
                material = value.get("material_or_specification", raw_candidate.get("material_or_spec"))
                component_id = value.get("component_id")
            else:  # ACCEPTED -- raw extraction never resolves component_id (R5B's own no-fabrication rule)
                item_position = raw_candidate.get("item_position")
                description = raw_candidate.get("description")
                quantity = _parse_quantity(raw_candidate.get("quantity_raw"))
                material = raw_candidate.get("material_or_spec")

            if component_id is not None:
                # R5D.1A Section 3: an EXPLICITLY reviewed/resolved
                # component_id is a canonical reference decision, not a
                # best-effort guess -- if it no longer resolves, that is a
                # genuine data-integrity problem the whole promotion must
                # refuse, never a silent downgrade to "unresolved" (which
                # would misrepresent a human's own resolved decision as
                # if it had never been made). Only the absence of an
                # explicit component_id at all (CASE A) legitimately
                # promotes with component_id=NULL.
                cur.execute("SELECT 1 FROM internal_component_master WHERE component_id = %s", (component_id,))
                if cur.fetchone() is None:
                    raise ReferenceNotFound(
                        f"{candidate_id} bom_candidates[{index}] explicitly reviewed component_id "
                        f"{component_id!r} does not exist in internal_component_master"
                    )

            code = _deterministic_code("ENGBOM", "candidate", candidate_id, "index", str(index))
            cur.execute(
                "INSERT INTO engineering_drawing_bom_line "
                "(bom_line_code, revision_code, item_position, component_id, component_description, quantity, "
                "material_or_specification, created_by, updated_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (bom_line_code) DO NOTHING RETURNING bom_line_code",
                (code, revision_code, item_position, component_id, description, quantity, material, promoted_by, promoted_by),
            )
            cur.fetchone()
            codes.append(code)
        return codes

    # ---- references / links ----

    def _resolve_references(self, reviewed_references: dict, extracted_references: list) -> tuple[list[dict], list[dict]]:
        """Only CORRECTED references with an explicit, complete
        {target_type, target_code, relationship_type} value are ever
        promotable -- an ACCEPTED reference has no target of its own to
        accept (R5B's ReferenceCandidate never carries one), so it is
        never linked, matching this file's own module docstring."""
        resolved: list[dict] = []
        warnings: list[dict] = []
        for index_str, decision in reviewed_references.items():
            status = decision.get("review_status")
            if status in (None, "REJECTED"):
                continue
            if status == "ACCEPTED":
                warnings.append({"field": f"references[{index_str}]", "message": "ACCEPTED reference has no resolvable target; not linked"})
                continue
            # CORRECTED
            value = decision.get("value") or {}
            target_type = value.get("target_type")
            target_code = value.get("target_code")
            relationship_type = value.get("relationship_type")
            if not target_type or not target_code or not relationship_type:
                raise InvalidReviewPayload(f"references[{index_str}] is missing target_type/target_code/relationship_type")
            if target_type not in _TARGET_AUTHORITY:
                raise InvalidReviewPayload(f"references[{index_str}] has invalid target_type {target_type!r}")
            if relationship_type not in _ALLOWED_RELATIONSHIP_TYPES:
                raise InvalidReviewPayload(f"references[{index_str}] has invalid relationship_type {relationship_type!r}")
            resolved.append({"target_type": target_type, "target_code": target_code, "relationship_type": relationship_type})
        return resolved, warnings

    def _validate_references(self, cur, resolved_references: list[dict]) -> None:
        for ref in resolved_references:
            table, column = _TARGET_AUTHORITY[ref["target_type"]]
            cur.execute(f"SELECT 1 FROM {table} WHERE {column} = %s", (ref["target_code"],))  # noqa: S608 -- table/column from a closed internal map, never user input
            if cur.fetchone() is None:
                raise ReferenceNotFound(f"{ref['target_type']}:{ref['target_code']} does not exist in {table}.{column}")

    def _insert_links(self, cur, candidate_id: str, drawing_code: str, resolved_references: list[dict], promoted_by: str) -> list[str]:
        codes: list[str] = []
        for index, ref in enumerate(resolved_references):
            code = _deterministic_code("ENGLINK", "candidate", candidate_id, "index", str(index))
            cur.execute(
                "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type, created_by, updated_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (drawing_code, target_type, target_code, relationship_type) WHERE retracted_at IS NULL DO NOTHING "
                "RETURNING link_code",
                (code, drawing_code, ref["target_type"], ref["target_code"], ref["relationship_type"], promoted_by, promoted_by),
            )
            row = cur.fetchone()
            codes.append(row["link_code"] if row is not None else code)
        return codes

    # ---- scope ----

    def _enforce_scope(
        self, cur, drawing_code: str, drawing_created: bool, resolved_references: list[dict], actor_scope: frozenset[str] | None,
    ) -> None:
        if actor_scope is None:
            return
        areas: set[str] = set()
        if not drawing_created:
            cur.execute(
                "SELECT DISTINCT a.area FROM engineering_drawing_link l JOIN asset_registry a ON a.asset_code = l.target_code "
                "WHERE l.drawing_code = %s AND l.target_type = 'ASSET' AND l.retracted_at IS NULL",
                (drawing_code,),
            )
            areas.update(row["area"] for row in cur.fetchall() if row["area"])
        for ref in resolved_references:
            if ref["target_type"] != "ASSET":
                continue
            cur.execute("SELECT area FROM asset_registry WHERE asset_code = %s", (ref["target_code"],))
            row = cur.fetchone()
            if row and row["area"]:
                areas.add(row["area"])
        if not areas or not (areas & actor_scope):
            raise ScopeDenied(f"drawing {drawing_code} has no determinable area within the actor's scope")

    # ---- spine / status ----

    def _insert_promotion_row(self, cur, candidate_id: str, drawing_code: str, revision_code: str, artifact_code: str, promoted_by: str) -> str:
        import psycopg2

        code = _deterministic_code("ENGPROMO", "candidate", candidate_id)
        try:
            cur.execute(
                "INSERT INTO engineering_drawing_promotion "
                "(promotion_code, candidate_id, drawing_code, revision_code, artifact_code, promoted_by, promoted_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                (code, candidate_id, drawing_code, revision_code, artifact_code, promoted_by),
            )
        except psycopg2.errors.UniqueViolation as exc:
            # Defensive only -- the candidate's own FOR UPDATE lock (held
            # since the start of this transaction) plus the earlier
            # _find_existing_promotion() check already make this
            # unreachable in practice; never silently retried.
            raise PromotionConcurrencyConflict(f"{candidate_id} already has a promotion row") from exc
        return code

    def _transition_candidate_saved(self, cur, candidate_id: str, promoted_by: str) -> None:
        cur.execute(
            "UPDATE document_field_extraction SET status = 'SAVED', updated_at = NOW() "
            "WHERE document_field_extraction_id = %s AND status = 'REVIEWED'",
            (candidate_id,),
        )
        if cur.rowcount != 1:
            raise PromotionConcurrencyConflict(f"{candidate_id} could not be transitioned to SAVED (rowcount={cur.rowcount})")


def _parse_quantity(quantity_raw: str | None) -> float | None:
    if not quantity_raw:
        return None
    cleaned = "".join(ch for ch in quantity_raw if ch.isdigit() or ch == ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


__all__ = [
    "EngineeringDrawingPromotionService",
    "CandidateNotFound",
    "CandidateNotEligible",
    "CandidateRejected",
    "InvalidReviewPayload",
    "DrawingMatchRequiresReview",
    "RevisionMatchRequiresReview",
    "CanonicalConflict",
    "ReferenceNotFound",
    "ScopeDenied",
    "AlreadyPromoted",
    "PromotionConcurrencyConflict",
]

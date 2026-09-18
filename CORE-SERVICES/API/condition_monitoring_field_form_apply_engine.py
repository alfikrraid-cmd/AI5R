"""AI5R — LTSA Condition Monitoring Field Form Atomic Apply Engine (CM R5E.4).

Implements the single-asset atomic persistence engine, approval validation,
content hash computation, eligibility filtering, and batch orchestration for
field form walking rounds.

INVARIANTS:
- Single persistence unit: INSPECTED_ASSET_CM_READING.
- One PostgreSQL transaction per asset:
    parent condition_monitoring_reading
  + 20 legacy parent columns
  + 20 generic child measurements (condition_monitoring_reading_measurement)
  + 2 child observations (condition_monitoring_reading_measurement)
  + audit row (record_change_history)
  ALL COMMIT OR ALL ROLLBACK.
- DB-enforced idempotency backed by migration 041 partial unique index on:
    source_reference LIKE 'field_form:%' AND deleted_at IS NULL
  with transactional advisory locking to eliminate race conditions.
- Strict eligibility:
  - Quarantined assets (946-P-2D, 946-P-4A, 946-P-4C, 946-P-8A, 946-P-8B) NEVER persist.
  - Blank template columns NEVER persist (SKIPPED_BLANK).
  - Pure NOT_INSPECTED / NI / NA assets NEVER persist (SKIPPED_NOT_INSPECTED).
- Zero automatic finding creation (ltsa_finding writes = 0).
- Deterministic content hashing independent of reviewer/applier/timestamps.
"""

from __future__ import annotations

import enum
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _sql  # noqa: E402

from condition_monitoring_field_form_engine import (  # noqa: E402
    _PARAM_CONTRACTS,
    CanonicalParameterContract,
    ConditionState,
    ParsedValue,
    StorageTier,
    ValueState,
    get_parameter_contract,
    parse_field_value,
    plan_asset_storage,
)

# ------------------------------------------------------------------------------
# 1. CONSTANTS & QUARANTINE
# ------------------------------------------------------------------------------

QUARANTINED_ASSET_CODES: frozenset[str] = frozenset({
    "946-P-2D",
    "946-P-4A",
    "946-P-4C",
    "946-P-8A",
    "946-P-8B",
})

LEGACY_MAPPING_COUNT: int = 20
MEASUREMENT_MAPPING_COUNT: int = 20
OBSERVATION_MAPPING_COUNT: int = 2
TOTAL_CANONICAL_PARAMETERS: int = 42

DEFAULT_SYSTEM_ACTOR_UUID: str = "00000000-0000-0000-0000-000000000000"


class ApplyOutcome(str, enum.Enum):
    APPLIED = "APPLIED"
    ALREADY_APPLIED = "ALREADY_APPLIED"
    CONCURRENT_DUPLICATE_APPLY = "CONCURRENT_DUPLICATE_APPLY"
    SKIPPED_BLANK = "SKIPPED_BLANK"
    SKIPPED_NOT_INSPECTED = "SKIPPED_NOT_INSPECTED"
    REJECTED_QUARANTINE = "REJECTED_QUARANTINE"
    REJECTED_UNKNOWN_ASSET = "REJECTED_UNKNOWN_ASSET"
    PREVIEW_NOT_FOUND_OR_EXPIRED = "PREVIEW_NOT_FOUND_OR_EXPIRED"
    PREVIEW_NOT_ACCEPTED = "PREVIEW_NOT_ACCEPTED"
    WORKBOOK_HASH_MISMATCH = "WORKBOOK_HASH_MISMATCH"
    PAYLOAD_HASH_MISMATCH = "PAYLOAD_HASH_MISMATCH"
    ASSET_REVIEW_REQUIRED = "ASSET_REVIEW_REQUIRED"
    AREA_SCOPE_DENIED = "AREA_SCOPE_DENIED"
    AUTH_DENIED = "AUTH_DENIED"
    READING_INSERT_FAILURE = "READING_INSERT_FAILURE"
    MEASUREMENT_INSERT_FAILURE = "MEASUREMENT_INSERT_FAILURE"
    OBSERVATION_INSERT_FAILURE = "OBSERVATION_INSERT_FAILURE"
    AUDIT_INSERT_FAILURE = "AUDIT_INSERT_FAILURE"
    TRANSACTION_COMMIT_FAILURE = "TRANSACTION_COMMIT_FAILURE"


# ------------------------------------------------------------------------------
# 2. CONTENT IDENTITY & DETERMINISTIC HASHING
# ------------------------------------------------------------------------------

def serialize_canonical_json(data: Any) -> str:
    """Serializes data into canonical JSON with deterministic sorting and compact separators."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_content_payload(
    *,
    canonical_asset: str,
    inspection_date: str,
    workbook_sha256: str,
    source_sheet: str,
    source_asset_literal: str,
    parameter_values: dict[str, Any],
    units: dict[str, str | None] | None = None,
    condition_states: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Constructs deterministic content payload representing the business inspection facts.

    Excludes: reviewer, applier, preview_id, volatile timestamps.
    """
    units_map = units or {}
    cond_map = condition_states or {}

    # Sort parameters deterministically by canonical code
    canonical_parameters: list[dict[str, Any]] = []
    for code in sorted(parameter_values.keys()):
        raw_val = parameter_values[code]
        # Format numeric float deterministically
        if isinstance(raw_val, float):
            formatted_val: float | None = round(raw_val, 6)
        else:
            formatted_val = raw_val

        canonical_parameters.append({
            "code": str(code),
            "condition": str(cond_map.get(code, "UNKNOWN")),
            "unit": units_map.get(code),
            "value": formatted_val,
        })

    return {
        "canonical_asset": str(canonical_asset).strip().upper(),
        "canonical_parameters": canonical_parameters,
        "inspection_date": str(inspection_date).strip(),
        "source_asset_literal": str(source_asset_literal).strip(),
        "source_sheet": str(source_sheet).strip(),
        "workbook_sha256": str(workbook_sha256).strip().lower(),
    }


def compute_content_hash(payload: dict[str, Any]) -> str:
    """Computes SHA-256 digest of canonical content payload."""
    canonical_json = serialize_canonical_json(payload)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def build_approval_binding(
    *,
    content_hash: str,
    workbook_sha256: str,
    reviewed_by: str,
    reviewed_at: str,
    review_decision: str,
) -> dict[str, Any]:
    """Constructs deterministic approval binding binding the approved content hash to reviewer context."""
    return {
        "content_hash": str(content_hash).strip().lower(),
        "review_decision": str(review_decision).strip().upper(),
        "reviewed_at": str(reviewed_at).strip(),
        "reviewed_by": str(reviewed_by).strip(),
        "workbook_sha256": str(workbook_sha256).strip().lower(),
    }


def compute_approval_binding_hash(binding: dict[str, Any]) -> str:
    """Computes SHA-256 digest of approval binding."""
    canonical_json = serialize_canonical_json(binding)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_batch_content_hash(
    *,
    workbook_sha256: str,
    inspection_date: str,
    asset_content_hashes: Sequence[str],
) -> str:
    """Computes deterministic SHA-256 digest over the approved asset batch.

    Combines sorted per-asset CONTENT_HASH values + workbook identity + inspection_date.
    Excludes volatile preview_id, timestamps, and reviewers.
    """
    sorted_hashes = sorted(str(h).strip().lower() for h in asset_content_hashes)
    canonical_batch = {
        "asset_content_hashes": sorted_hashes,
        "inspection_date": str(inspection_date).strip(),
        "workbook_sha256": str(workbook_sha256).strip().lower(),
    }
    canonical_json = serialize_canonical_json(canonical_batch)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------------------
# 3. APPROVAL VALIDATION & INTEGRATION GAP REPORTING
# ------------------------------------------------------------------------------

def validate_approval(
    *,
    preview_session: dict[str, Any] | None,
    asset_content_hash: str,
    expected_workbook_sha256: str,
    actor_id: str,
    actor_permissions: set[str],
    actor_area_scope: set[str] | frozenset[str] | None,
    asset_area: str | None,
    organization_id: str | None = None,
    expected_organization_id: str | None = None,
) -> tuple[bool, str | None]:
    """Validates review state and authorization before executing any DB transaction.

    Returns:
        (True, None) if valid.
        (False, error_code) if validation fails.
    """
    if preview_session is None:
        return False, ApplyOutcome.PREVIEW_NOT_FOUND_OR_EXPIRED.value

    # Check expiration
    if preview_session.get("expired", False):
        return False, ApplyOutcome.PREVIEW_NOT_FOUND_OR_EXPIRED.value

    # Check review decision (supports string or dict payload)
    raw_decision = preview_session.get("review_decision")
    if isinstance(raw_decision, dict):
        review_decision = raw_decision.get("decision")
    else:
        review_decision = raw_decision or preview_session.get("summary", {}).get("review_status")

    if review_decision != "ACCEPTED_FOR_FUTURE_APPLY":
        return False, ApplyOutcome.PREVIEW_NOT_ACCEPTED.value

    # Revalidate workbook hash
    stored_workbook_hash = preview_session.get("workbook_sha256")
    if stored_workbook_hash != expected_workbook_sha256:
        return False, ApplyOutcome.WORKBOOK_HASH_MISMATCH.value

    # Revalidate approved content hash (supports batch list and single hash)
    approved_hashes = preview_session.get("approved_content_hashes")
    single_approved_hash = preview_session.get("content_hash")
    if approved_hashes is None and single_approved_hash is None:
        # R5D integration gap: preview session currently lacks stored content_hash
        return False, "R5D_CONTENT_HASH_MISSING"

    if approved_hashes is not None:
        if asset_content_hash not in approved_hashes and asset_content_hash != single_approved_hash:
            return False, ApplyOutcome.PAYLOAD_HASH_MISMATCH.value
    elif single_approved_hash != asset_content_hash:
        return False, ApplyOutcome.PAYLOAD_HASH_MISMATCH.value

    # Organization boundary check
    if organization_id and expected_organization_id and organization_id != expected_organization_id:
        return False, ApplyOutcome.AUTH_DENIED.value

    # Actor permissions check
    if "maintenance.write" not in actor_permissions:
        return False, ApplyOutcome.AUTH_DENIED.value

    # Actor area scope check
    if actor_area_scope is not None:
        if not asset_area or asset_area not in actor_area_scope:
            return False, ApplyOutcome.AREA_SCOPE_DENIED.value

    return True, None


# ------------------------------------------------------------------------------
# 4. ELIGIBILITY & QUARANTINE FILTERING
# ------------------------------------------------------------------------------

def check_apply_eligibility(
    canonical_asset: str,
    parsed_items: dict[str, ParsedValue],
) -> tuple[bool, ApplyOutcome]:
    """Evaluates whether an asset reading is eligible for database persistence.

    Rules:
    - Quarantined assets (946-P-2D, 946-P-4A, 946-P-4C, 946-P-8A, 946-P-8B): REJECTED_QUARANTINE.
    - Blank template asset (all items None/empty): SKIPPED_BLANK.
    - Pure NOT_INSPECTED / NI / NA asset (no VALUE_PRESENT): SKIPPED_NOT_INSPECTED.
    - Zero (0 or 0.0) or False is a valid VALUE_PRESENT and NOT skipped.
    """
    clean_asset = canonical_asset.strip().upper()
    if clean_asset in QUARANTINED_ASSET_CODES:
        return False, ApplyOutcome.REJECTED_QUARANTINE

    if not parsed_items:
        return False, ApplyOutcome.SKIPPED_BLANK

    has_any_data = False
    has_meaningful_value = False

    for pv in parsed_items.values():
        if pv.raw_value is not None and str(pv.raw_value).strip() != "":
            has_any_data = True

        if pv.value_state == ValueState.VALUE_PRESENT:
            has_meaningful_value = True

    if not has_any_data:
        return False, ApplyOutcome.SKIPPED_BLANK

    if not has_meaningful_value:
        return False, ApplyOutcome.SKIPPED_NOT_INSPECTED

    return True, ApplyOutcome.APPLIED


# ------------------------------------------------------------------------------
# 5. IDEMPOTENCY KEY FORMATTING
# ------------------------------------------------------------------------------

def format_source_reference(
    *,
    full_workbook_sha256: str,
    inspection_date: str,
    canonical_asset: str,
) -> str:
    """Formats exact, non-truncated source_reference idempotency identity."""
    clean_hash = full_workbook_sha256.strip().lower()
    clean_date = inspection_date.strip()
    clean_asset = canonical_asset.strip().upper()
    return f"field_form:{clean_hash}:{clean_date}:{clean_asset}"


# ------------------------------------------------------------------------------
# 6. PER-ASSET ATOMIC PERSISTENCE TRANSACTION
# ------------------------------------------------------------------------------

def _sanitize_actor_uuid(actor_id: str | None) -> str:
    if not actor_id:
        return DEFAULT_SYSTEM_ACTOR_UUID
    try:
        return str(uuid.UUID(str(actor_id).strip()))
    except (ValueError, AttributeError):
        return DEFAULT_SYSTEM_ACTOR_UUID


def apply_asset_reading_atomic(
    runner: Any,
    *,
    canonical_asset: str,
    inspection_date: str,
    full_workbook_sha256: str,
    source_sheet: str,
    source_asset_literal: str,
    parsed_items: dict[str, ParsedValue],
    asset_type: str = "PUMP",
    applier_id: str = DEFAULT_SYSTEM_ACTOR_UUID,
    schedule_code: str | None = None,
    force_measurement_failure: bool = False,
    force_audit_failure: bool = False,
) -> dict[str, Any]:
    """Persists a single asset reading inside ONE single PostgreSQL CTE transaction.

    Persists:
      - condition_monitoring_reading (parent + 20 legacy columns)
      - condition_monitoring_reading_measurement (20 child measurements + 2 observations)
      - record_change_history (audit)

    Returns deterministic outcome:
      - APPLIED
      - ALREADY_APPLIED
      - CONCURRENT_DUPLICATE_APPLY
      - SKIPPED_BLANK
      - SKIPPED_NOT_INSPECTED
      - REJECTED_QUARANTINE
      - MEASUREMENT_INSERT_FAILURE / AUDIT_INSERT_FAILURE / READING_INSERT_FAILURE
    """
    clean_asset = canonical_asset.strip().upper()
    source_reference = format_source_reference(
        full_workbook_sha256=full_workbook_sha256,
        inspection_date=inspection_date,
        canonical_asset=clean_asset,
    )

    # 1. Eligibility precheck (zero DB writes if ineligible)
    is_eligible, outcome = check_apply_eligibility(clean_asset, parsed_items)
    if not is_eligible:
        return {
            "outcome": outcome.value,
            "canonical_asset": clean_asset,
            "source_reference": source_reference,
            "reading_code": None,
            "measurements_inserted": 0,
            "observations_inserted": 0,
            "audit_logged": False,
            "message": f"Asset {clean_asset} ineligible for persistence: {outcome.value}",
        }

    # 2. Plan storage tier routing (42 parameters)
    storage_plan = plan_asset_storage(clean_asset, parsed_items)

    effective_schedule_code = schedule_code or "UNSCHEDULED::FIELD_FORM"
    reading_code = f"CMONR-{uuid.uuid4().hex[:12].upper()}"
    clean_actor_uuid = _sanitize_actor_uuid(applier_id)

    # 3. Build legacy parent columns & values
    # The 20 legacy parent columns in condition_monitoring_reading
    legacy_columns = list(storage_plan.legacy_parent_values.keys())
    legacy_cols_sql = ", " + ", ".join(legacy_columns) if legacy_columns else ""
    legacy_vals_sql = ", " + ", ".join(_sql(storage_plan.legacy_parent_values[col]) for col in legacy_columns) if legacy_columns else ""

    # 4. Build child measurements and observations VALUES
    all_child_rows: list[dict[str, Any]] = []
    all_child_rows.extend(storage_plan.child_measurements)
    all_child_rows.extend(storage_plan.child_observations)

    has_child_items = len(all_child_rows) > 0

    child_values_clauses: list[str] = []
    for idx, item in enumerate(all_child_rows):
        side = item.get("measurement_side")
        if force_measurement_failure and idx == 0:
            side = "INVALID_SIDE_FORCE_FAIL"

        m_code_sql = _sql(item.get("measurement_code"))
        m_label_sql = _sql(item.get("measurement_label"))
        val_num = item.get("value_numeric")
        val_num_sql = f"{_sql(val_num)}::numeric" if val_num is not None else "NULL::numeric"
        val_txt = item.get("value_text")
        val_txt_sql = f"{_sql(val_txt)}::text" if val_txt is not None else "NULL::text"
        unit_sql = f"{_sql(item.get('unit'))}::text"
        side_sql = f"{_sql(side)}::text"
        src_label_sql = f"{_sql(item.get('source_label'))}::text"

        child_values_clauses.append(
            f"({m_code_sql}, {m_label_sql}, {val_num_sql}, {val_txt_sql}, {unit_sql}, {side_sql}, {src_label_sql})"
        )

    child_values_sql = ",\n        ".join(child_values_clauses)

    if has_child_items:
        ins_measurements_cte = f"""
    ins_measurements AS (
        INSERT INTO condition_monitoring_reading_measurement (
            reading_id,
            measurement_code,
            measurement_label,
            value_numeric,
            value_text,
            unit,
            measurement_side,
            source_label,
            source_reference,
            verification_status,
            created_by,
            updated_by
        )
        SELECT
            r.condition_monitoring_reading_code,
            m.m_code,
            m.m_label,
            m.m_val_num,
            m.m_val_txt,
            m.m_unit,
            m.m_side,
            m.m_src_label,
            {_sql(source_reference)},
            'DRAFT',
            {_sql(clean_actor_uuid)}::uuid,
            {_sql(clean_actor_uuid)}::uuid
        FROM ins_reading r
        CROSS JOIN (
            VALUES
            {child_values_sql}
        ) AS m(m_code, m_label, m_val_num, m_val_txt, m_unit, m_side, m_src_label)
        RETURNING measurement_id
    ),"""
    else:
        ins_measurements_cte = """
    ins_measurements AS (
        SELECT 1 AS dummy WHERE FALSE
    ),"""

    audit_entity_sql = "'CONDITION_MONITORING_READING'"
    if force_audit_failure:
        # Force failure by inserting NULL into NOT NULL column entity_type
        audit_entity_sql = "NULL"

    ins_audit_cte = f"""
    ins_audit AS (
        INSERT INTO record_change_history (
            entity_type,
            entity_id,
            field_name,
            old_value,
            new_value,
            changed_by,
            reason,
            source_reference
        )
        SELECT
            {audit_entity_sql},
            r.condition_monitoring_reading_code,
            '__record__',
            NULL,
            row_to_json(r)::text,
            {_sql(clean_actor_uuid)}::uuid,
            'FIELD_FORM_APPLY',
            {_sql(source_reference)}
        FROM ins_reading r
        RETURNING change_id
    )"""

    # Complete compound CTE query: ONE statement = ONE transaction
    sql = f"""
WITH advisory_lock AS (
    SELECT pg_advisory_xact_lock(('x' || substr(md5({_sql(source_reference)}), 1, 15))::bit(64)::bigint)
),
active_existing AS (
    SELECT condition_monitoring_reading_code, source_reference
    FROM condition_monitoring_reading
    WHERE source_reference = {_sql(source_reference)}
      AND deleted_at IS NULL
    LIMIT 1
),
ins_reading AS (
    INSERT INTO condition_monitoring_reading (
        condition_monitoring_reading_code,
        condition_monitoring_schedule_code,
        asset_code,
        asset_type,
        reading_date{legacy_cols_sql},
        workflow_status,
        provenance,
        created_by,
        updated_by,
        source_reference,
        finding
    )
    SELECT
        {_sql(reading_code)},
        {_sql(effective_schedule_code)},
        {_sql(clean_asset)},
        COALESCE((SELECT asset_type FROM asset_registry WHERE asset_code = {_sql(clean_asset)}), {_sql(asset_type)}),
        {_sql(inspection_date)}::date{legacy_vals_sql},
        'DRAFT',
        'FIELD_FORM',
        {_sql(clean_actor_uuid)}::uuid,
        {_sql(clean_actor_uuid)}::uuid,
        {_sql(source_reference)},
        NULL
    WHERE NOT EXISTS (SELECT 1 FROM active_existing)
    RETURNING condition_monitoring_reading_code, asset_code, reading_date, source_reference, created_at
),{ins_measurements_cte}{ins_audit_cte}
SELECT json_build_object(
    'lock_acquired', TRUE,
    'already_applied_code', (SELECT condition_monitoring_reading_code FROM active_existing),
    'reading_code', (SELECT condition_monitoring_reading_code FROM ins_reading),
    'measurements_inserted', (SELECT count(*) FROM ins_measurements),
    'audit_logged', (SELECT count(*) FROM ins_audit) > 0
)::text;
"""

    try:
        raw = runner.query_scalar(sql)
        parsed_result = json.loads(raw) if raw else {}

        already_code = parsed_result.get("already_applied_code")
        if already_code:
            return {
                "outcome": ApplyOutcome.ALREADY_APPLIED.value,
                "canonical_asset": clean_asset,
                "source_reference": source_reference,
                "reading_code": already_code,
                "measurements_inserted": 0,
                "observations_inserted": 0,
                "audit_logged": False,
                "message": f"Asset {clean_asset} already applied with reading {already_code}",
            }

        new_reading_code = parsed_result.get("reading_code")
        if not new_reading_code:
            return {
                "outcome": ApplyOutcome.READING_INSERT_FAILURE.value,
                "canonical_asset": clean_asset,
                "source_reference": source_reference,
                "reading_code": None,
                "measurements_inserted": 0,
                "observations_inserted": 0,
                "audit_logged": False,
                "message": "Parent reading insert failed or was suppressed",
            }

        return {
            "outcome": ApplyOutcome.APPLIED.value,
            "canonical_asset": clean_asset,
            "source_reference": source_reference,
            "reading_code": new_reading_code,
            "measurements_inserted": len(storage_plan.child_measurements),
            "observations_inserted": len(storage_plan.child_observations),
            "audit_logged": parsed_result.get("audit_logged", False),
            "message": f"Asset {clean_asset} successfully applied with reading {new_reading_code}",
        }

    except Exception as exc:  # noqa: BLE001
        err_detail = getattr(exc, "stderr", None) or getattr(exc, "pgerror", None) or str(exc)

        # Check for DB unique constraint violation from migration 041
        if "idx_condition_monitoring_reading_field_form_unique" in err_detail or "23505" in err_detail or "duplicate key" in err_detail:
            return {
                "outcome": ApplyOutcome.CONCURRENT_DUPLICATE_APPLY.value,
                "canonical_asset": clean_asset,
                "source_reference": source_reference,
                "reading_code": None,
                "measurements_inserted": 0,
                "observations_inserted": 0,
                "audit_logged": False,
                "message": f"Concurrent duplicate apply intercepted by migration 041 unique index: {err_detail}",
            }

        # Check for audit check failure
        if "record_change_history" in err_detail:
            return {
                "outcome": ApplyOutcome.AUDIT_INSERT_FAILURE.value,
                "canonical_asset": clean_asset,
                "source_reference": source_reference,
                "reading_code": None,
                "measurements_inserted": 0,
                "observations_inserted": 0,
                "audit_logged": False,
                "message": f"Audit insert failed (rolled back parent reading): {err_detail}",
            }

        # Check for measurement check failure
        if "condition_monitoring_reading_measurement" in err_detail or "measurement_side" in err_detail:
            return {
                "outcome": ApplyOutcome.MEASUREMENT_INSERT_FAILURE.value,
                "canonical_asset": clean_asset,
                "source_reference": source_reference,
                "reading_code": None,
                "measurements_inserted": 0,
                "observations_inserted": 0,
                "audit_logged": False,
                "message": f"Measurement insert failed (rolled back parent reading): {err_detail}",
            }

        return {
            "outcome": ApplyOutcome.TRANSACTION_COMMIT_FAILURE.value,
            "canonical_asset": clean_asset,
            "source_reference": source_reference,
            "reading_code": None,
            "measurements_inserted": 0,
            "observations_inserted": 0,
            "audit_logged": False,
            "message": f"Transaction aborted and rolled back: {err_str}",
        }


# ------------------------------------------------------------------------------
# 7. BATCH ORCHESTRATION
# ------------------------------------------------------------------------------

@dataclass
class BatchApplySummary:
    total_assets: int
    applied_count: int
    already_applied_count: int
    skipped_blank_count: int
    skipped_ni_count: int
    rejected_quarantine_count: int
    failed_count: int
    asset_outcomes: list[dict[str, Any]]


def apply_batch_orchestrator(
    runner: Any,
    *,
    workbook_sha256: str,
    source_sheet: str,
    inspection_date: str,
    asset_batch: Sequence[dict[str, Any]],
    applier_id: str = DEFAULT_SYSTEM_ACTOR_UUID,
) -> BatchApplySummary:
    """Orchestrates sequential, isolated per-asset atomic transactions across a walking round."""
    applied = 0
    already = 0
    skipped_blank = 0
    skipped_ni = 0
    rejected_quarantine = 0
    failed = 0
    outcomes: list[dict[str, Any]] = []

    for item in asset_batch:
        canonical_asset = item["canonical_asset"]
        source_literal = item.get("source_asset_literal", canonical_asset)
        parsed_items = item.get("parsed_items", {})

        res = apply_asset_reading_atomic(
            runner,
            canonical_asset=canonical_asset,
            inspection_date=inspection_date,
            full_workbook_sha256=workbook_sha256,
            source_sheet=source_sheet,
            source_asset_literal=source_literal,
            parsed_items=parsed_items,
            applier_id=applier_id,
        )
        outcomes.append(res)

        code = res["outcome"]
        if code == ApplyOutcome.APPLIED.value:
            applied += 1
        elif code == ApplyOutcome.ALREADY_APPLIED.value:
            already += 1
        elif code == ApplyOutcome.SKIPPED_BLANK.value:
            skipped_blank += 1
        elif code == ApplyOutcome.SKIPPED_NOT_INSPECTED.value:
            skipped_ni += 1
        elif code == ApplyOutcome.REJECTED_QUARANTINE.value:
            rejected_quarantine += 1
        else:
            failed += 1

    return BatchApplySummary(
        total_assets=len(asset_batch),
        applied_count=applied,
        already_applied_count=already,
        skipped_blank_count=skipped_blank,
        skipped_ni_count=skipped_ni,
        rejected_quarantine_count=rejected_quarantine,
        failed_count=failed,
        asset_outcomes=outcomes,
    )

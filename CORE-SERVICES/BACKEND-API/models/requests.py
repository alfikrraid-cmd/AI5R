from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# MWO-LTSA-AUTH-001


class LoginRequest(BaseModel):
    email: str | None = None
    identifier: str | None = None
    password: str


# MWO-AI5R-LTSA-COPILOT-001 -- asset_context is optional: global dashboard
# questions omit it, an asset workspace sends the currently-selected pump
# tag automatically (see CopilotPanel.jsx/useCopilot.js). Never trusted as
# an authorization scope by itself -- the router re-resolves and enforces
# the caller's own server-side area scope against it before any data read.
class CopilotAskRequest(BaseModel):
    question: str
    asset_context: str | None = None


# MWO-LTSA-AUTH-003A-FINAL -- Admin Users API request bodies. `password`/
# `new_password` are plain strings ONLY in the request (never persisted or
# logged as-is -- the router hashes via auth_password.hash_password()
# before any repository call; no response model ever echoes a password
# field back).
class AdminCreateUserRequest(BaseModel):
    username: str
    email: str | None = None
    password: str
    organization_id: str
    role: str


class AdminUpdateUserStatusRequest(BaseModel):
    status: str


class AdminUpdateMembershipRoleRequest(BaseModel):
    organization_id: str
    role: str


class AdminResetPasswordRequest(BaseModel):
    new_password: str


# MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- manual completion of
# seal_registry.kimap_pertamina/gpn_john_crane. Both fields are always
# submitted together (the caller sends the seal's whole desired
# identifier state, not a sparse per-field patch) -- str | None with
# default None so an omitted field means "clear it", the same
# empty-string/None equivalence seal_master_data_repository.
# normalize_identifier_field enforces server-side. Never carries
# quantity_on_hand or any seal_stock field -- Phase 10's "stock quantity
# is not editable through this API" is a fact about this model's shape,
# not just a router check.
class SealIdentifierUpdateRequest(BaseModel):
    kimap_pertamina: str | None = None
    gpn_john_crane: str | None = None


# MWO-LTSA-PHYSICAL-SEAL-001B -- registration only: no status, no
# current_pump_tag_number, no lifecycle/installation/warranty field.
# Registration and installation are separate domain actions (this MWO's
# own explicit rule) -- there is nothing on this model a client could
# even attempt to use as an implicit installation mechanism.
class SealUnitRegisterRequest(BaseModel):
    seal_code: str
    serial_number: str | None = None


# MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001 -- created_by is deliberately
# NOT a field here (server-derived from the authenticated actor only,
# never client-supplied -- same discipline SealIdentifierUpdateRequest's
# own updated_by omission already established).
class SealLifecycleEventCreateRequest(BaseModel):
    event_type: str
    event_at: str
    pump_tag_number: str | None = None
    reason: str | None = None
    notes: str | None = None
    source_reference: str | None = None


# MWO-LTSA-SEAL-INSPECTION-REPAIR-001 -- created_by is deliberately NOT a
# field on either create request here, same discipline
# SealLifecycleEventCreateRequest's own omission already established.
class SealInspectionFindingRequest(BaseModel):
    component: str
    condition: str | None = None
    measurement_name: str | None = None
    measured_value: float | None = None
    unit: str | None = None
    acceptance_min: float | None = None
    acceptance_max: float | None = None
    finding: str | None = None
    action_required: str | None = None


class SealInspectionCreateRequest(BaseModel):
    inspection_date: str
    inspection_type: str
    pump_tag_number: str | None = None
    overall_condition: str | None = None
    failure_mode: str | None = None
    root_cause: str | None = None
    recommendation: str | None = None
    disposition: str | None = None
    inspected_by: str | None = None
    notes: str | None = None
    source_reference: str | None = None
    findings: list[SealInspectionFindingRequest] = Field(default_factory=list)


class SealRepairCreateRequest(BaseModel):
    repair_date: str
    repair_type: str
    repair_action: str
    inspection_id: str | None = None
    parts_replaced: list[Any] | dict[str, Any] | None = None
    repair_result: str | None = None
    performed_by: str | None = None
    notes: str | None = None
    source_reference: str | None = None


# MWO-LTSA-SEAL-WARRANTY-ASSESSMENT-001 -- created_by/decided_by are
# deliberately NOT fields here, same server-derived-actor discipline
# every prior seal-domain create request already established.
class SealWarrantyAssessmentCreateRequest(BaseModel):
    installation_event_id: str
    claim_date: str | None = None
    failure_date: str | None = None
    inspection_id: str | None = None
    source_reference: str | None = None


class SealWarrantyDecisionRequest(BaseModel):
    decision: str
    decision_reason: str
    inspection_id: str | None = None


# MWO-LTSA-SEAL-INSTALLATION-FITMENT-001 -- linked_by is deliberately NOT
# a field here (server-derived actor, same discipline every prior
# seal-domain write request already established).
class InstallationReportLinkRequest(BaseModel):
    seal_unit_id: str
    installation_event_id: str
    pump_tag_number: str
    reason: str

# Fields mirror exactly what WorkOrderGateway.create_work_order already
# accepts (per the canonical Work Order Create workflow's Validate node) --
# not new business fields, just typed for the request body.


class WorkOrderCreateRequest(BaseModel):
    work_order_code: str
    description: str
    customer_code: str | None = None
    asset_code: str | None = None
    asset_type: str | None = None
    priority: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    # title / work_type / due_date added per ADR-WO-003 (implements WO-BE-004).
    # Nullable, matching the new work_order columns -- omitting them preserves
    # existing caller behavior unchanged.
    title: str | None = None
    work_type: str | None = None
    due_date: str | None = None


# Fields mirror exactly what MaintenanceHistoryGateway.create_maintenance_history
# already accepts (per the canonical Maintenance History Create workflow's
# Validate node).


class MaintenanceCreateRequest(BaseModel):
    maintenance_record_code: str
    action_taken: str
    work_order_code: str | None = None
    asset_code: str | None = None
    asset_type: str | None = None
    performed_by: str | None = None
    notes: str | None = None


# Import API Foundation -- request shapes mirror API.import_validator's own
# ImportPackage exactly (pumps/seals/installations/documents, each a list
# of raw snake_case records) -- not a new/renamed shape, just a typed
# request body for the same four lists parse_import_package() already
# accepts as a plain dict.


class ImportPackageRequest(BaseModel):
    pumps: list[dict[str, Any]] = Field(default_factory=list)
    seals: list[dict[str, Any]] = Field(default_factory=list)
    installations: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)


# Fields mirror API.conflict_resolution.build_conflict_report's own two
# positional parameters (database_snapshot, incoming_package), both the
# same ImportPackage shape.


class ImportConflictCheckRequest(BaseModel):
    database_snapshot: ImportPackageRequest
    incoming_package: ImportPackageRequest


# Fields mirror API.import_session.build_import_session's own required
# keyword arguments (session_id/created_at/source/status/created_by) plus
# one ImportPackage to validate and wrap into the session -- session_id/
# created_at are caller-supplied, never generated here, per
# import_session.py's own "no uuid.uuid4()/datetime.now()" determinism
# rule.
#
# MWO-LTSA-103A -- database_snapshot added, same ImportPackageRequest shape
# ImportConflictCheckRequest already uses for its own field of the same
# name (reused, not a new type). Optional, defaulting to an empty package
# (every list empty) -- a caller with no live-database snapshot to supply
# gets a real ConflictReport computed against nothing, where every incoming
# record legitimately resolves as CREATE_NEW, rather than this endpoint
# skipping conflict-checking altogether.


class ImportSessionCreateRequest(BaseModel):
    session_id: str
    created_at: str
    source: str
    status: str
    created_by: str | None = None
    package: ImportPackageRequest
    database_snapshot: ImportPackageRequest = Field(default_factory=ImportPackageRequest)


class ImportExecuteRequest(BaseModel):
    session_id: str


# MWO-LTSA-PM-CM-INTAKE-001 -- PM Occurrence / Condition Monitoring
# Reading draft-create/update/submit/review request bodies. Neither model
# has an updated_by/submitted_by/reviewed_by/technical_reviewed_by field
# anywhere -- every actor is always server-derived from the authenticated
# identity (Phase 26/Hard Rule 15), so there is nothing for a client to
# spoof by including one; pydantic silently drops any extra field a
# caller sends anyway (e.g. a smuggled "submitted_by").
class PMActivityEntry(BaseModel):
    # Golden evidence (Laporan PM, CM & Pemasangan Seal, page 34/35): a
    # fixed, named 33-item checklist -- code/description identify which
    # item, side is DE/NDE/None (most items are side-less, e.g. "Quench
    # Line"; a few are explicitly split, e.g. "Flushing Line DE Side").
    code: str
    description: str
    side: str | None = None
    done: bool = False


class PMOccurrenceCreateRequest(BaseModel):
    pm_schedule_code: str
    asset_code: str
    asset_type: str | None = None
    occurrence_date: str | None = None
    activities: list[PMActivityEntry] | None = None
    remarks: str | None = None


class PMScheduleCreateRequest(BaseModel):
    pm_schedule_code: str
    asset_code: str
    asset_type: str | None = None
    procedure: str
    frequency: str
    trigger_type: str
    interval_unit: str | None = None
    effective_date: str | None = None
    next_due: str | None = None
    assigned_to: str | None = None
    provenance: str = "MANUAL"
    source_reference: str | None = None


class PMScheduleUpdateRequest(BaseModel):
    procedure: str | None = None
    frequency: str | None = None
    trigger_type: str | None = None
    interval_unit: str | None = None
    effective_date: str | None = None
    next_due: str | None = None
    assigned_to: str | None = None
    status: str | None = None


class ConditionMonitoringScheduleCreateRequest(BaseModel):
    condition_monitoring_schedule_code: str
    asset_code: str
    asset_type: str | None = None
    monitoring_type: str
    measurement_point: str | None = None
    frequency: str | None = None
    interval_unit: str | None = None
    effective_date: str | None = None
    # MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- mirrors
    # PMScheduleCreateRequest's own next_due field exactly; drives the
    # PLANNED/ACTIVE/OVERDUE computation the same way for Condition
    # Monitoring as it already does for PM.
    next_due: str | None = None
    provenance: str = "MANUAL"
    source_reference: str | None = None


class ConditionMonitoringScheduleUpdateRequest(BaseModel):
    monitoring_type: str | None = None
    measurement_point: str | None = None
    frequency: str | None = None
    interval_unit: str | None = None
    effective_date: str | None = None
    # MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- mirrors
    # PMScheduleUpdateRequest's own next_due/status fields exactly. status
    # is the real stored value (PLANNED/ACTIVE/COMPLETED/CANCELLED) --
    # OVERDUE is computed client-side, never legitimate to write back
    # (same convention pmMapping.js's own rawStatus comment establishes).
    next_due: str | None = None
    status: str | None = None


class PMOccurrenceUpdateRequest(BaseModel):
    occurrence_date: str | None = None
    activities: list[PMActivityEntry] | None = None
    finding: str | None = None
    preliminary_recommendation: str | None = None
    remarks: str | None = None


class AdminReturnForCorrectionRequest(BaseModel):
    return_reason: str


class TechnicalReviewRequest(BaseModel):
    # action is a real command the server interprets, never a client-
    # written workflow_status string (Phase 26) -- RETURN/ACKNOWLEDGE/
    # APPROVE are the only three technical actions John Crane can take
    # (Phase 13).
    action: str = Field(pattern="^(RETURN|ACKNOWLEDGE|APPROVE)$")
    comment: str | None = None
    recommendation: str | None = None


# Every Check Points field the golden "Mechanical Seal Condition
# Monitoring" report's DE/NDE table exposes (this MWO's Phase 1 audit),
# matching condition_monitoring_reading_repository.py's own
# _MEASUREMENT_COLUMNS tuple exactly -- kept as named fields (not a bare
# dict) so FastAPI validates types (NUMERIC columns as float, the two
# leak flags as bool) before anything reaches SQL.
class ConditionMonitoringMeasurements(BaseModel):
    flushing_temp_de: float | None = None
    flushing_temp_nde: float | None = None
    quench_temp_de: float | None = None
    quench_temp_nde: float | None = None
    flushing_in_temp_de: float | None = None
    flushing_in_temp_nde: float | None = None
    flushing_out_temp_de: float | None = None
    flushing_out_temp_nde: float | None = None
    cooling_water_in_temp_de: float | None = None
    cooling_water_in_temp_nde: float | None = None
    cooling_water_out_temp_de: float | None = None
    cooling_water_out_temp_nde: float | None = None
    mechseal_temp_de: float | None = None
    mechseal_temp_nde: float | None = None
    mechanical_seal_leak_de: bool | None = None
    mechanical_seal_leak_nde: bool | None = None
    water_jacket_temp_de: float | None = None
    water_jacket_temp_nde: float | None = None
    suction_temp: float | None = None
    discharge_temp: float | None = None
    pump_operating_state: str | None = None
    suction_pressure: float | None = None
    discharge_pressure: float | None = None
    quench_pressure_de: float | None = None
    quench_pressure_nde: float | None = None
    stuffing_box_temp_de: float | None = None
    stuffing_box_temp_nde: float | None = None
    seal_gland_temp_de: float | None = None
    seal_gland_temp_nde: float | None = None
    vertical_vibration_de: float | None = None
    vertical_vibration_nde: float | None = None
    horizontal_vibration_de: float | None = None
    horizontal_vibration_nde: float | None = None
    axial_vibration_de: float | None = None
    axial_vibration_nde: float | None = None
    bearing_temp_de: float | None = None
    bearing_temp_nde: float | None = None
    motor_current: float | None = None


class ConditionMonitoringReadingCreateRequest(BaseModel):
    condition_monitoring_schedule_code: str
    asset_code: str
    asset_type: str | None = None
    reading_date: str | None = None
    measurements: ConditionMonitoringMeasurements = Field(default_factory=ConditionMonitoringMeasurements)


class ConditionMonitoringReadingUpdateRequest(BaseModel):
    reading_date: str | None = None
    measurements: ConditionMonitoringMeasurements = Field(default_factory=ConditionMonitoringMeasurements)
    finding: str | None = None

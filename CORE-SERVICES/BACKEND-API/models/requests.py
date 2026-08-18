from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# MWO-LTSA-AUTH-001


class LoginRequest(BaseModel):
    email: str
    password: str


# MWO-LTSA-AUTH-003A-FINAL -- Admin Users API request bodies. `password`/
# `new_password` are plain strings ONLY in the request (never persisted or
# logged as-is -- the router hashes via auth_password.hash_password()
# before any repository call; no response model ever echoes a password
# field back).
class AdminCreateUserRequest(BaseModel):
    email: str
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
# database_snapshot: same ImportPackageRequest shape ImportConflictCheckRequest
# already uses for its own field of the same name (reused, not a new type).
# Optional, defaulting to an empty package (every list empty) -- a caller
# with no live-database snapshot to supply gets a real ConflictReport
# computed against nothing, where every incoming record legitimately
# resolves as CREATE_NEW, rather than this endpoint skipping conflict-
# checking altogether.


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

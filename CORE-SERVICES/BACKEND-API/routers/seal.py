from __future__ import annotations

import dataclasses

from fastapi import APIRouter, Depends, HTTPException

from dependencies import (
    get_current_user,
    get_import_database_runner,
    get_installation_report_fitment_repository,
    get_pump_gateway,
    get_seal_gateway,
    get_seal_inspection_repository,
    get_seal_lifecycle_event_repository,
    get_seal_master_data_repository,
    get_seal_pump_compatibility_gateway,
    get_seal_repair_repository,
    get_seal_stock_gateway,
    get_seal_unit_repository,
    get_seal_warranty_assessment_repository,
    require_permission,
)
from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import filter_records_by_asset_scope, is_area_in_scope, resolve_asset_area
from API.seal_equipment_history_service import build_seal_unit_history
from API.seal_lifecycle_service import (
    IncompatiblePumpError,
    InvalidLifecycleTransitionError,
    MissingReasonError,
    SealLifecycleError,
    SealUnitNotFoundError,
    apply_lifecycle_event,
)
from API.seal_inspection_service import (
    InvalidInspectionStateError,
    InvalidVocabularyError as InvalidInspectionVocabularyError,
    SealInspectionError,
    SealInspectionFinding,
    SealUnitNotFoundError as InspectionSealUnitNotFoundError,
    UnknownPumpError,
    create_inspection,
)
from API.seal_repair_service import (
    InspectionMismatchError,
    InvalidRepairStateError,
    InvalidVocabularyError as InvalidRepairVocabularyError,
    SealRepairError,
    SealUnitNotFoundError as RepairSealUnitNotFoundError,
    create_repair,
)
from API.seal_warranty_service import (
    AlreadyDecidedError,
    AssessmentNotFoundError,
    InspectionMismatchError as WarrantyInspectionMismatchError,
    InstallationEventMismatchError,
    InstallationEventNotFoundError,
    InvalidChronologyError,
    InvalidDecisionError,
    MissingDecisionReasonError,
    MissingInspectionForDecisionError,
    NotAnInstallEventError,
    SealUnitNotFoundError as WarrantySealUnitNotFoundError,
    SealWarrantyError,
    create_warranty_assessment,
    decide_assessment,
)
from API.seal_master_data_repository import normalize_identifier_field
from models.requests import (
    SealIdentifierUpdateRequest,
    SealInspectionCreateRequest,
    SealLifecycleEventCreateRequest,
    SealRepairCreateRequest,
    SealWarrantyAssessmentCreateRequest,
    SealWarrantyDecisionRequest,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001 -- seal.read gates seal identity/compatibility data
# for the whole router; seal-stock additionally requires inventory.read
# (stacked below), since stock QUANTITY is a distinct permission from
# seal IDENTITY in this MWO's own requested permission set.
router = APIRouter(dependencies=[Depends(require_permission("seal.read"))])

# Mechanical Seal Workspace API (MWO-LTSA-041, per MWO-LTSA-040's
# archaeology) -- reuses SealGateway/SealStockGateway/
# SealPumpCompatibilityGateway unmodified, exposed under the /api/ltsa
# prefix already used by every other LTSA registry endpoint (mirrors
# pumps.py's list_ltsa_pumps pass-through exactly). No new gateway,
# service, repository, workflow, or SQL -- these three Gateways and their
# n8n workflows already existed; only the router layer was missing. List
# only, matching each Gateway's own real capability -- create/detail/
# update/delete are out of this MWO's scope.


@router.get("/api/ltsa/seals")
def list_ltsa_seals(seal_gateway=Depends(get_seal_gateway)) -> Payload:
    return seal_gateway.list_seals()


# MWO-LTSA-SEAL-UNIT-IDENTITY-FOUNDATION-001 -- read support only (no
# create/install/remove/repair route) for the new physical-seal-identity
# primitive. Deliberately UNSCOPED, mirroring list_ltsa_seals/
# list_ltsa_seal_stock above, not list_ltsa_seal_compatibility's
# per-pump-row scoping: seal_unit's primary identity is seal-catalog-
# shaped (like seal_registry), and a unit's current_pump_tag_number is
# explicitly current-state-only, not the row's ownership. This mirrors
# the existing, already-intentional "seal.read exposes the seal catalog
# globally" policy rather than silently introducing a new one -- flagged
# in this MWO's own completion report for explicit Chief Architect
# confirmation, not decided unilaterally here.
@router.get("/api/ltsa/seal-units")
def list_ltsa_seal_units(seal_unit_repository=Depends(get_seal_unit_repository)) -> Payload:
    data = seal_unit_repository.list_all()
    return {"data": data, "count": len(data)}


@router.get("/api/ltsa/seal-units/{seal_unit_id}")
def get_ltsa_seal_unit(seal_unit_id: str, seal_unit_repository=Depends(get_seal_unit_repository)) -> Payload:
    unit = seal_unit_repository.find_by_id(seal_unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="No such seal unit")
    return {"data": unit}


@router.get("/api/ltsa/seal-stock")
def list_ltsa_seal_stock(
    seal_stock_gateway=Depends(get_seal_stock_gateway),
    _stock_permission=Depends(require_permission("inventory.read")),
) -> Payload:
    return seal_stock_gateway.list_seal_stocks()


@router.get("/api/ltsa/seal-compatibility")
def list_ltsa_seal_compatibility(
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- each row carries
    # pump_tag_number (not asset_code); list_ltsa_seals/list_ltsa_seal_stock
    # above are deliberately left unscoped (a seal_code has no single-area
    # ownership of its own -- "DO NOT invent ownership"), but a
    # compatibility ROW is genuinely single-pump-attributable.
    response = seal_pump_compatibility_gateway.list_seal_pump_compatibilities()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        filtered = filter_records_by_asset_scope(
            response["data"], scope, pump_gateway, asset_field="pump_tag_number"
        )
        response = {**response, "data": filtered, "count": len(filtered)}
    return response


# MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- the first write route this
# router has ever had. Gated on master.edit, not seal.read: master.edit
# was reserved in advance for exactly this ("master DATA edit --
# pumps/seals canonical definitions, no current route", auth_service.py's
# own ROLE_PERMISSIONS header) and is currently granted only to SUPERUSER
# and TAP_ADMIN (confirmed by reading the real ROLE_PERMISSIONS dict --
# TAP_ENGINEER is NOT in that set today) -- TAP_ENGINEER, JOHN_CRANE_
# ENGINEER, and both Pertamina roles are read-only here without a new
# permission string having to be invented, and without widening an
# existing one to fit this UI (Phase 6's own explicit allowance).
# Bypasses SealGateway/n8n entirely (see
# seal_master_data_repository.py's own header for why) -- reads still go
# through GET /api/ltsa/seals unchanged (SELECT * there already returns
# the two new columns once migration 013 has run, no gateway/workflow
# edit needed).
@router.patch("/api/ltsa/seals/{seal_code}")
def update_seal_identifiers(
    seal_code: str,
    payload: SealIdentifierUpdateRequest,
    current_user=Depends(require_permission("master.edit")),
    seal_master_data_repository=Depends(get_seal_master_data_repository),
) -> Payload:
    updated = seal_master_data_repository.update_seal_identifiers(
        seal_code,
        kimap_pertamina=normalize_identifier_field(payload.kimap_pertamina),
        gpn_john_crane=normalize_identifier_field(payload.gpn_john_crane),
        # Server-derived from the verified bearer token, never from the
        # request body -- SealIdentifierUpdateRequest has no updated_by
        # field at all, so there is nothing for a client to spoof here
        # (Phase 18: "client cannot submit arbitrary creator identity").
        updated_by=current_user.user_id,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="No such seal")
    return {"data": updated}


# --- MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001 -- append-only lifecycle event ledger ---
#
# AREA AUTHORIZATION (documented, not silently decided): seal_unit
# identity itself stays GLOBAL under seal.read (Chief-Architect-frozen,
# #6.1's closure). A lifecycle EVENT is different -- when it carries a
# real pump_tag_number (INSTALL/REMOVE), that pump association is real,
# current, pump-area-attributable information, so it is scoped exactly
# like every other pump-attributable row in this codebase (list_ltsa_
# seal_compatibility's own precedent, reused). An event with NO pump
# (REGISTERED, SEND_FOR_INSPECTION, etc.) carries no pump-area
# information to leak in the first place, so it is never filtered --
# hiding it would not protect anything and would just make an
# unrestricted-shaped row behave inconsistently. Never derived from
# seal_unit.current_pump_tag_number (a current-state snapshot, not
# authorization truth, per this MWO's own explicit rule).
def _visible_events(events: list[dict], scope, pump_gateway) -> list[dict]:
    if scope is None:
        return events
    visible = []
    for event in events:
        pump_tag = event.get("pump_tag_number")
        if pump_tag is None:
            visible.append(event)
            continue
        if is_area_in_scope(resolve_asset_area(pump_tag, pump_gateway), scope):
            visible.append(event)
    return visible


@router.get("/api/ltsa/seal-units/{seal_unit_id}/lifecycle")
def list_seal_unit_lifecycle(
    seal_unit_id: str,
    seal_unit_repository=Depends(get_seal_unit_repository),
    seal_lifecycle_event_repository=Depends(get_seal_lifecycle_event_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    if seal_unit_repository.find_by_id(seal_unit_id) is None:
        raise HTTPException(status_code=404, detail="No such seal unit")
    events = seal_lifecycle_event_repository.list_by_seal_unit(seal_unit_id)
    scope = resolve_area_scope(current_user)
    events = _visible_events(events, scope, pump_gateway)
    return {"data": events, "count": len(events)}


@router.get("/api/ltsa/seal-lifecycle-events/{event_id}")
def get_seal_lifecycle_event(
    event_id: str,
    seal_lifecycle_event_repository=Depends(get_seal_lifecycle_event_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    event = seal_lifecycle_event_repository.find_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="No such seal lifecycle event")
    scope = resolve_area_scope(current_user)
    if not _visible_events([event], scope, pump_gateway):
        # Same 404 a genuinely-missing event gets -- never disclose that
        # an out-of-scope event exists at all (existing scope discipline,
        # e.g. get_ltsa_pump_detail's own identical choice elsewhere).
        raise HTTPException(status_code=404, detail="No such seal lifecycle event")
    return {"data": event}


@router.post("/api/ltsa/seal-units/{seal_unit_id}/lifecycle")
def create_seal_unit_lifecycle_event(
    seal_unit_id: str,
    payload: SealLifecycleEventCreateRequest,
    current_user=Depends(require_permission("seal.lifecycle_write")),
    runner=Depends(get_import_database_runner),
) -> Payload:
    try:
        event = apply_lifecycle_event(
            runner,
            seal_unit_id=seal_unit_id,
            event_type=payload.event_type,
            event_at=payload.event_at,
            # Server-derived, never request-supplied -- SealLifecycleEventCreateRequest
            # has no created_by field at all (Phase 18: no actor-spoofing surface).
            created_by=current_user.user_id,
            pump_tag_number=payload.pump_tag_number,
            reason=payload.reason,
            notes=payload.notes,
            source_reference=payload.source_reference,
        )
    except SealUnitNotFoundError:
        raise HTTPException(status_code=404, detail="No such seal unit")
    except MissingReasonError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except InvalidLifecycleTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except IncompatiblePumpError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except SealLifecycleError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": event}


# --- MWO-LTSA-SEAL-INSPECTION-REPAIR-001 -- engineering inspection/repair records ---
#
# Same area-authorization shape as #6.2's lifecycle events (_visible_events
# reused unchanged, not duplicated): a pump-associated record is scoped to
# that pump's area; a pumpless record stays globally readable under
# seal.read (seal_repair has no pump_tag_number column at all -- every
# repair row is treated as pumpless here, consistent with #6.2's own
# pumpless policy, never seal_unit.current_pump).


@router.get("/api/ltsa/seal-units/{seal_unit_id}/inspections")
def list_seal_unit_inspections(
    seal_unit_id: str,
    seal_unit_repository=Depends(get_seal_unit_repository),
    seal_inspection_repository=Depends(get_seal_inspection_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    if seal_unit_repository.find_by_id(seal_unit_id) is None:
        raise HTTPException(status_code=404, detail="No such seal unit")
    inspections = seal_inspection_repository.list_by_seal_unit(seal_unit_id)
    scope = resolve_area_scope(current_user)
    inspections = _visible_events(inspections, scope, pump_gateway)
    return {"data": inspections, "count": len(inspections)}


@router.get("/api/ltsa/seal-inspections/{inspection_id}")
def get_seal_inspection(
    inspection_id: str,
    seal_inspection_repository=Depends(get_seal_inspection_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    inspection = seal_inspection_repository.find_by_id(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="No such seal inspection")
    scope = resolve_area_scope(current_user)
    if not _visible_events([inspection], scope, pump_gateway):
        raise HTTPException(status_code=404, detail="No such seal inspection")
    return {"data": inspection}


@router.post("/api/ltsa/seal-units/{seal_unit_id}/inspections")
def create_seal_unit_inspection(
    seal_unit_id: str,
    payload: SealInspectionCreateRequest,
    current_user=Depends(require_permission("seal.lifecycle_write")),
    runner=Depends(get_import_database_runner),
) -> Payload:
    try:
        inspection = create_inspection(
            runner,
            seal_unit_id=seal_unit_id,
            inspection_date=payload.inspection_date,
            inspection_type=payload.inspection_type,
            # Server-derived, never request-supplied -- SealInspectionCreateRequest
            # has no created_by field at all (same actor-spoof discipline).
            created_by=current_user.user_id,
            pump_tag_number=payload.pump_tag_number,
            overall_condition=payload.overall_condition,
            failure_mode=payload.failure_mode,
            root_cause=payload.root_cause,
            recommendation=payload.recommendation,
            disposition=payload.disposition,
            inspected_by=payload.inspected_by,
            notes=payload.notes,
            source_reference=payload.source_reference,
            findings=[
                SealInspectionFinding(
                    component=f.component, condition=f.condition, measurement_name=f.measurement_name,
                    measured_value=f.measured_value, unit=f.unit, acceptance_min=f.acceptance_min,
                    acceptance_max=f.acceptance_max, finding=f.finding, action_required=f.action_required,
                )
                for f in payload.findings
            ],
        )
    except InspectionSealUnitNotFoundError:
        raise HTTPException(status_code=404, detail="No such seal unit")
    except InvalidInspectionStateError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except (UnknownPumpError, InvalidInspectionVocabularyError) as error:
        raise HTTPException(status_code=422, detail=str(error))
    except SealInspectionError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": inspection}


@router.get("/api/ltsa/seal-units/{seal_unit_id}/repairs")
def list_seal_unit_repairs(
    seal_unit_id: str,
    seal_unit_repository=Depends(get_seal_unit_repository),
    seal_repair_repository=Depends(get_seal_repair_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    if seal_unit_repository.find_by_id(seal_unit_id) is None:
        raise HTTPException(status_code=404, detail="No such seal unit")
    # seal_repair carries no pump_tag_number column (this MWO's own field
    # list) -- every repair row is pumpless, so seal.read alone already
    # governs visibility; no per-row scope filter is meaningful here.
    repairs = seal_repair_repository.list_by_seal_unit(seal_unit_id)
    return {"data": repairs, "count": len(repairs)}


@router.get("/api/ltsa/seal-repairs/{repair_id}")
def get_seal_repair(
    repair_id: str,
    seal_repair_repository=Depends(get_seal_repair_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    repair = seal_repair_repository.find_by_id(repair_id)
    if repair is None:
        raise HTTPException(status_code=404, detail="No such seal repair")
    return {"data": repair}


@router.post("/api/ltsa/seal-units/{seal_unit_id}/repairs")
def create_seal_unit_repair(
    seal_unit_id: str,
    payload: SealRepairCreateRequest,
    current_user=Depends(require_permission("seal.lifecycle_write")),
    runner=Depends(get_import_database_runner),
) -> Payload:
    try:
        repair = create_repair(
            runner,
            seal_unit_id=seal_unit_id,
            repair_date=payload.repair_date,
            repair_type=payload.repair_type,
            repair_action=payload.repair_action,
            # Server-derived, never request-supplied.
            created_by=current_user.user_id,
            inspection_id=payload.inspection_id,
            parts_replaced=payload.parts_replaced,
            repair_result=payload.repair_result,
            performed_by=payload.performed_by,
            notes=payload.notes,
            source_reference=payload.source_reference,
        )
    except RepairSealUnitNotFoundError:
        raise HTTPException(status_code=404, detail="No such seal unit")
    except InvalidRepairStateError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except InspectionMismatchError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except InvalidRepairVocabularyError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except SealRepairError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": repair}


# --- MWO-LTSA-SEAL-WARRANTY-ASSESSMENT-001 -- warranty window + technical assessment ---
#
# AREA AUTHORIZATION: derived from the linked INSTALL event's own
# pump_tag_number (SealWarrantyAssessmentRepository's own JOIN, exposed
# as installation_pump_tag_number) -- never seal_unit.current_pump_
# tag_number (this MWO's own explicit rule). INSTALL always requires a
# pump (#6.2's own pump_required=True rule), so a genuinely pumpless
# warranty row cannot occur in practice; _visible_by_installation_pump
# still handles a hypothetical None safely (never visible-by-default to
# a restricted identity), matching #6.2/#6.3's own fail-closed discipline
# rather than assuming "pumpless" here the way a REGISTERED lifecycle
# event legitimately is.
def _visible_by_installation_pump(records: list[dict], scope, pump_gateway) -> list[dict]:
    if scope is None:
        return records
    visible = []
    for record in records:
        pump_tag = record.get("installation_pump_tag_number")
        if is_area_in_scope(resolve_asset_area(pump_tag, pump_gateway) if pump_tag else None, scope):
            visible.append(record)
    return visible


@router.get("/api/ltsa/seal-units/{seal_unit_id}/warranty")
def list_seal_unit_warranty_assessments(
    seal_unit_id: str,
    seal_unit_repository=Depends(get_seal_unit_repository),
    seal_warranty_assessment_repository=Depends(get_seal_warranty_assessment_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    if seal_unit_repository.find_by_id(seal_unit_id) is None:
        raise HTTPException(status_code=404, detail="No such seal unit")
    assessments = seal_warranty_assessment_repository.list_by_seal_unit(seal_unit_id)
    scope = resolve_area_scope(current_user)
    assessments = _visible_by_installation_pump(assessments, scope, pump_gateway)
    return {"data": assessments, "count": len(assessments)}


@router.get("/api/ltsa/seal-warranty-assessments/{assessment_id}")
def get_seal_warranty_assessment(
    assessment_id: str,
    seal_warranty_assessment_repository=Depends(get_seal_warranty_assessment_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    assessment = seal_warranty_assessment_repository.find_by_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="No such seal warranty assessment")
    scope = resolve_area_scope(current_user)
    if not _visible_by_installation_pump([assessment], scope, pump_gateway):
        raise HTTPException(status_code=404, detail="No such seal warranty assessment")
    return {"data": assessment}


@router.post("/api/ltsa/seal-units/{seal_unit_id}/warranty")
def create_seal_unit_warranty_assessment(
    seal_unit_id: str,
    payload: SealWarrantyAssessmentCreateRequest,
    current_user=Depends(require_permission("seal.lifecycle_write")),
    runner=Depends(get_import_database_runner),
) -> Payload:
    try:
        assessment = create_warranty_assessment(
            runner,
            seal_unit_id=seal_unit_id,
            installation_event_id=payload.installation_event_id,
            # Server-derived, never request-supplied.
            created_by=current_user.user_id,
            claim_date=payload.claim_date,
            failure_date=payload.failure_date,
            inspection_id=payload.inspection_id,
            source_reference=payload.source_reference,
        )
    except WarrantySealUnitNotFoundError:
        raise HTTPException(status_code=404, detail="No such seal unit")
    except InstallationEventNotFoundError:
        raise HTTPException(status_code=404, detail="No such installation event")
    except (NotAnInstallEventError, InstallationEventMismatchError) as error:
        raise HTTPException(status_code=422, detail=str(error))
    except WarrantyInspectionMismatchError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except InvalidChronologyError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except SealWarrantyError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": assessment}


@router.post("/api/ltsa/seal-warranty-assessments/{assessment_id}/decision")
def decide_seal_warranty_assessment(
    assessment_id: str,
    payload: SealWarrantyDecisionRequest,
    current_user=Depends(require_permission("seal.lifecycle_write")),
    runner=Depends(get_import_database_runner),
) -> Payload:
    try:
        assessment = decide_assessment(
            runner,
            assessment_id=assessment_id,
            decision=payload.decision,
            decision_reason=payload.decision_reason,
            # Server-derived, never request-supplied.
            decided_by=current_user.user_id,
            inspection_id=payload.inspection_id,
        )
    except AssessmentNotFoundError:
        raise HTTPException(status_code=404, detail="No such seal warranty assessment")
    except AlreadyDecidedError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except MissingInspectionForDecisionError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except MissingDecisionReasonError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except InvalidDecisionError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except WarrantyInspectionMismatchError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except SealWarrantyError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": assessment}


# --- MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- cross-pump physical seal history ---
#
# Read-model only, no write path. Every event's own `payload.pump_
# tag_number` (a normalized key seal_equipment_history_service.py
# guarantees on every event type, including seal_repair which has no
# such column of its own -- see that module's own comments) is what
# scope is checked against here, never seal_unit.current_pump_tag_number.
# A pumpless event (payload.pump_tag_number is None -- e.g. REGISTERED
# is excluded entirely, but a repair with no linked inspection, or a
# pumpless inspection, legitimately has none) stays globally visible
# under seal.read, the same #6.2/#6.3 policy already established.


@router.get("/api/ltsa/seal-units/{seal_unit_id}/history")
def get_seal_unit_history(
    seal_unit_id: str,
    seal_unit_repository=Depends(get_seal_unit_repository),
    seal_lifecycle_event_repository=Depends(get_seal_lifecycle_event_repository),
    seal_inspection_repository=Depends(get_seal_inspection_repository),
    seal_repair_repository=Depends(get_seal_repair_repository),
    seal_warranty_assessment_repository=Depends(get_seal_warranty_assessment_repository),
    installation_report_fitment_repository=Depends(get_installation_report_fitment_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    if seal_unit_repository.find_by_id(seal_unit_id) is None:
        raise HTTPException(status_code=404, detail="No such seal unit")

    events = build_seal_unit_history(
        seal_unit_id,
        seal_lifecycle_event_repository=seal_lifecycle_event_repository,
        seal_inspection_repository=seal_inspection_repository,
        seal_repair_repository=seal_repair_repository,
        seal_warranty_assessment_repository=seal_warranty_assessment_repository,
        installation_report_fitment_repository=installation_report_fitment_repository,
    )

    scope = resolve_area_scope(current_user)
    if scope is not None:
        visible = []
        for event in events:
            pump_tag = event.payload.get("pump_tag_number")
            # Pumpless stays globally visible under seal.read (#6.2's own
            # established policy, reused verbatim) -- this is a deliberate
            # bypass of the scope check entirely, NOT a call to
            # is_area_in_scope(None, scope), which fails closed for a
            # restricted identity and would incorrectly hide it.
            if pump_tag is None:
                visible.append(event)
                continue
            if is_area_in_scope(resolve_asset_area(pump_tag, pump_gateway), scope):
                visible.append(event)
        events = tuple(visible)

    data = [dataclasses.asdict(event) for event in events]
    return {"data": data, "count": len(data)}

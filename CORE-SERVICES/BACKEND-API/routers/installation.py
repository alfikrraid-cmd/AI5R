from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import filter_records_by_asset_scope, is_area_in_scope, is_asset_in_scope, resolve_asset_area
from API.installation_fitment_service import (
    AlreadyLinkedError,
    InstallationFitmentError,
    InstallationEventNotFoundError,
    InstallationReportNotFoundError,
    MissingReasonError,
    NotAnInstallEventError,
    PumpMismatchError,
    SealCodeContradictionError,
    SealUnitMismatchError,
    SealUnitNotFoundError as FitmentSealUnitNotFoundError,
    link_installation_report,
)
from dependencies import (
    get_current_user,
    get_import_database_runner,
    get_installation_gateway,
    get_installation_report_fitment_repository,
    get_pump_gateway,
    require_permission,
)
from models.requests import InstallationReportLinkRequest
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("drawing.read"))])

# Installation Report API (MWO-LTSA-060, production persistence path for
# the Installation Workspace created by MWO-LTSA-056) -- reuses
# InstallationGateway unmodified, exposed under the /api/ltsa prefix
# already used by every other LTSA registry endpoint (mirrors
# pm_schedule.py's list/detail pair exactly). List and detail only,
# matching InstallationGateway's own real capability -- create/update/
# delete are out of this MWO's scope.
#
# MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- installation_report's
# own pump-tag field is `plant_equip_no`, not `asset_code` (confirmed
# via EquipmentTimelineService's own field access) -- same 1-hop
# pump_gateway.get_pump() join, different field name.


@router.get("/api/ltsa/installations")
def list_ltsa_installations(
    installation_gateway=Depends(get_installation_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = installation_gateway.list_installations()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        filtered = filter_records_by_asset_scope(response["data"], scope, pump_gateway, asset_field="plant_equip_no")
        response = {**response, "data": filtered, "count": len(filtered)}
    return response


@router.get("/api/ltsa/installations/{installation_code}")
def get_ltsa_installation(
    installation_code: str,
    installation_gateway=Depends(get_installation_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = installation_gateway.get_installation(installation_code)
    scope = resolve_area_scope(current_user)
    data = response.get("data") if isinstance(response, dict) else None
    if scope is not None and isinstance(data, dict) and not is_asset_in_scope(data.get("plant_equip_no"), scope, pump_gateway):
        raise HTTPException(status_code=404, detail="Installation report not found")
    return response


# --- MWO-LTSA-SEAL-INSTALLATION-FITMENT-001 -- structured seal/pump/INSTALL-event linkage ---
#
# Distinct from the two n8n-gateway-backed routes above (which serve the
# full raw document by installation_code/list-all, scoped by the
# free-text plant_equip_no field): these routes expose the NEW
# structured relational queries (by seal_unit, by pump, by INSTALL
# event) this MWO requires, reusing the same installation_report table
# (no new table, no parallel "/fitments" resource). Scoped by the
# STRUCTURED pump_tag_number column, never plant_equip_no and never
# seal_unit.current_pump_tag_number -- a report with no structured pump
# (legacy/unlinked) fails closed for a scoped identity (is_area_in_scope's
# own "no area value -> never in scope for a restricted identity" rule),
# exactly this MWO's own explicit LEGACY REPORTS/AREA SCOPE requirement.


@router.get("/api/ltsa/seal-units/{seal_unit_id}/installation-reports")
def list_seal_unit_installation_reports(
    seal_unit_id: str,
    installation_report_fitment_repository=Depends(get_installation_report_fitment_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    reports = installation_report_fitment_repository.list_by_seal_unit(seal_unit_id)
    scope = resolve_area_scope(current_user)
    if scope is not None:
        reports = filter_records_by_asset_scope(reports, scope, pump_gateway, asset_field="pump_tag_number")
    return {"data": reports, "count": len(reports)}


@router.get("/api/ltsa/installation-reports/by-pump/{pump_tag_number}")
def list_installation_reports_by_pump(
    pump_tag_number: str,
    installation_report_fitment_repository=Depends(get_installation_report_fitment_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    if scope is not None and not is_area_in_scope(resolve_asset_area(pump_tag_number, pump_gateway), scope):
        return {"data": [], "count": 0}
    reports = installation_report_fitment_repository.list_by_pump(pump_tag_number)
    return {"data": reports, "count": len(reports)}


@router.get("/api/ltsa/installation-reports/{installation_code}")
def get_installation_report_fitment_detail(
    installation_code: str,
    installation_report_fitment_repository=Depends(get_installation_report_fitment_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    report = installation_report_fitment_repository.find_by_code(installation_code)
    if report is None:
        raise HTTPException(status_code=404, detail="No such installation report")
    scope = resolve_area_scope(current_user)
    if scope is not None and not is_asset_in_scope(report.get("pump_tag_number"), scope, pump_gateway):
        raise HTTPException(status_code=404, detail="No such installation report")
    return {"data": report}


@router.post("/api/ltsa/installation-reports/{installation_code}/link-installation")
def link_installation_report_to_install_event(
    installation_code: str,
    payload: InstallationReportLinkRequest,
    current_user=Depends(require_permission("seal.lifecycle_write")),
    runner=Depends(get_import_database_runner),
) -> Payload:
    try:
        report = link_installation_report(
            runner,
            installation_code=installation_code,
            seal_unit_id=payload.seal_unit_id,
            installation_event_id=payload.installation_event_id,
            pump_tag_number=payload.pump_tag_number,
            reason=payload.reason,
            # Server-derived, never request-supplied.
            linked_by=current_user.user_id,
        )
    except InstallationReportNotFoundError:
        raise HTTPException(status_code=404, detail="No such installation report")
    except FitmentSealUnitNotFoundError:
        raise HTTPException(status_code=404, detail="No such seal unit")
    except InstallationEventNotFoundError:
        raise HTTPException(status_code=404, detail="No such installation event")
    except AlreadyLinkedError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except (NotAnInstallEventError, SealUnitMismatchError, PumpMismatchError, SealCodeContradictionError) as error:
        raise HTTPException(status_code=422, detail=str(error))
    except MissingReasonError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except InstallationFitmentError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": report}

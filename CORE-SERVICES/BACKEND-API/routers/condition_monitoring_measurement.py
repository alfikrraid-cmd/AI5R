from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.condition_monitoring_measurement_repository import (
    ConditionMonitoringMeasurementRepository,
    EmptyMeasurementValue,
)
from dependencies import get_condition_monitoring_measurement_repository, get_current_user, require_permission
from models.responses import Payload

# MWO-LTSA-REPORTING-R4-1 -- wired into the real DI surface
# (dependencies.get_condition_monitoring_measurement_repository) and
# registered in main.py, now that both files are clean again. Still a
# new, bounded router (not an addition to the already-large
# routers/condition_monitoring.py), per R4's own Section 10 "OR create
# one bounded router" allowance -- only its DI wiring changed in R4-1.


router = APIRouter(dependencies=[Depends(require_permission("condition.read"))])


def _actor_id(current_user: AuthenticatedIdentity) -> str:
    return current_user.user_id


class ConditionMonitoringMeasurementCreateRequest(BaseModel):
    measurement_label: str
    measurement_code: str | None = None
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    measurement_side: str | None = None
    source_label: str | None = None
    source_reference: str | None = None
    verification_status: str = "DRAFT"


class ConditionMonitoringMeasurementUpdateRequest(BaseModel):
    measurement_label: str | None = None
    measurement_code: str | None = None
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    measurement_side: str | None = None
    source_label: str | None = None
    source_reference: str | None = None
    verification_status: str | None = None


@router.get("/api/ltsa/condition-monitoring/readings/{reading_id}/measurements")
def list_condition_monitoring_reading_measurements(
    reading_id: str,
    repository: ConditionMonitoringMeasurementRepository = Depends(get_condition_monitoring_measurement_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    rows = repository.list_by_reading(reading_id, scope=resolve_area_scope(current_user))
    if rows is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring reading not found")
    return {"success": True, "data": rows}


@router.get("/api/ltsa/condition-monitoring/measurements/{measurement_id}")
def get_condition_monitoring_reading_measurement(
    measurement_id: str,
    repository: ConditionMonitoringMeasurementRepository = Depends(get_condition_monitoring_measurement_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    data = repository.find_by_id(measurement_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Measurement not found")
    scope = resolve_area_scope(current_user)
    if scope is not None:
        visible = repository.list_by_reading(data["reading_id"], scope=scope) or []
        if not any(row["measurement_id"] == measurement_id for row in visible):
            raise HTTPException(status_code=404, detail="Measurement not found")
    return {"success": True, "data": data}


@router.post(
    "/api/ltsa/condition-monitoring/readings/{reading_id}/measurements",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_condition_monitoring_reading_measurement(
    reading_id: str,
    payload: ConditionMonitoringMeasurementCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: ConditionMonitoringMeasurementRepository = Depends(get_condition_monitoring_measurement_repository),
) -> Payload:
    try:
        created = repository.create(
            reading_id=reading_id,
            measurement_label=payload.measurement_label,
            measurement_code=payload.measurement_code,
            value_numeric=payload.value_numeric,
            value_text=payload.value_text,
            unit=payload.unit,
            measurement_side=payload.measurement_side,
            source_label=payload.source_label,
            source_reference=payload.source_reference,
            verification_status=payload.verification_status,
            created_by=_actor_id(current_user),
        )
    except EmptyMeasurementValue as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if created is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring reading not found")
    return {"success": True, "data": created}


@router.patch(
    "/api/ltsa/condition-monitoring/measurements/{measurement_id}",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def update_condition_monitoring_reading_measurement(
    measurement_id: str,
    payload: ConditionMonitoringMeasurementUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: ConditionMonitoringMeasurementRepository = Depends(get_condition_monitoring_measurement_repository),
) -> Payload:
    try:
        updated = repository.update(
            measurement_id,
            values=payload.model_dump(exclude_unset=True),
            updated_by=_actor_id(current_user),
        )
    except EmptyMeasurementValue as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if updated is None:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return {"success": True, "data": updated}

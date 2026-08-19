from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.record_edit_service import (
    FieldNotEditableError,
    OutOfScopeError,
    ReasonRequiredError,
    RecordNotFoundError,
    UnknownEntityTypeError,
    edit_value,
    get_history,
)
from dependencies import (
    get_current_user,
    get_import_database_runner,
    get_pump_gateway,
    get_record_change_history_repository,
    require_permission,
)
from models.responses import Payload

# MWO-LTSA-AUDIT-CHANGE-HISTORY-001 -- record.edit (SUPERUSER + TAP_ADMIN
# only) gates the correction endpoint; audit.read_full (SUPERUSER only,
# reused verbatim -- see auth_service.py's own ROLE_PERMISSIONS comment)
# gates history read. No router-level dependencies=[...] here (unlike
# most other routers) because the two routes need genuinely different
# permissions, not one shared gate.
router = APIRouter()


class RecordEditRequest(BaseModel):
    entity_type: str
    entity_id: str
    field_name: str
    new_value: Any = None
    reason: str = Field(min_length=1)
    source_reference: str | None = None


def _actor_id(current_user: AuthenticatedIdentity) -> str:
    return current_user.user_id


@router.post("/api/ltsa/records/edit")
def edit_record_value(
    payload: RecordEditRequest,
    current_user: AuthenticatedIdentity = Depends(require_permission("record.edit")),
    runner=Depends(get_import_database_runner),
    pump_gateway=Depends(get_pump_gateway),
) -> Payload:
    try:
        result = edit_value(
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            field_name=payload.field_name,
            new_value=payload.new_value,
            reason=payload.reason,
            # Server-derived only -- never trusts a client-supplied actor
            # identity, the same _actor_id(current_user) discipline
            # pm_occurrence.py/condition_monitoring.py's write routes
            # already establish.
            actor_id=_actor_id(current_user),
            scope=resolve_area_scope(current_user),
            runner=runner,
            pump_gateway=pump_gateway,
            source_reference=payload.source_reference,
        )
    except (RecordNotFoundError, OutOfScopeError) as error:
        # Same "no distinct signal for out-of-scope vs missing" rule this
        # session's own scope closures already established.
        raise HTTPException(status_code=404, detail=str(error))
    except (UnknownEntityTypeError, FieldNotEditableError, ReasonRequiredError) as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": result}


@router.get(
    "/api/ltsa/records/history",
    dependencies=[Depends(require_permission("audit.read_full"))],
)
def get_record_history(
    entity_type: str,
    entity_id: str,
    history_repository=Depends(get_record_change_history_repository),
) -> Payload:
    try:
        history = get_history(entity_type, entity_id, history_repository=history_repository)
    except UnknownEntityTypeError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": history}

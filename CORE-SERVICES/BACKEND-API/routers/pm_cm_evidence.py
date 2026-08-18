from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from dependencies import get_pm_cm_evidence_repository, require_permission
from API.pm_cm_evidence_repository import FileTooLargeError, UnsupportedContentTypeError
from models.responses import Payload

# MWO-LTSA-PM-CM-INTAKE-001 -- evidence attachments for PM Occurrence /
# Condition Monitoring Reading. Gated on maintenance.write (upload) and
# maintenance.read (list/download) -- the same permissions the PM/CMON
# records themselves use, not a new capability invented for evidence.
router = APIRouter()


@router.post("/api/ltsa/pm-cm-evidence", dependencies=[Depends(require_permission("maintenance.write"))])
async def upload_pm_cm_evidence(
    record_type: str = Form(...),
    record_code: str = Form(...),
    category: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user=Depends(require_permission("maintenance.write")),
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
) -> Payload:
    file_bytes = await file.read()
    try:
        created = pm_cm_evidence_repository.create(
            record_type=record_type,
            record_code=record_code,
            file_name=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            file_bytes=file_bytes,
            category=category,
            source="MANUAL",
            uploaded_by=current_user.user_id,
        )
    except (UnsupportedContentTypeError, FileTooLargeError) as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": created}


@router.get("/api/ltsa/pm-cm-evidence", dependencies=[Depends(require_permission("maintenance.read"))])
def list_pm_cm_evidence(
    record_type: str,
    record_code: str,
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
) -> Payload:
    return {"data": pm_cm_evidence_repository.list_for_record(record_type, record_code)}


@router.get(
    "/api/ltsa/pm-cm-evidence/{evidence_id}/download",
    dependencies=[Depends(require_permission("maintenance.read"))],
)
def download_pm_cm_evidence(
    evidence_id: str,
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
):
    record = pm_cm_evidence_repository.get_file_data(evidence_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No such evidence item")
    file_bytes = base64.b64decode(record["file_data_base64"])
    return Response(content=file_bytes, media_type=record["content_type"])

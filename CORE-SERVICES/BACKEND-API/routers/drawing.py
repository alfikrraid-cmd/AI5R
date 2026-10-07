"""LTSA Mechanical Seal Engineering Drawing API Router.

Implements dedicated endpoints for drawing document metadata, revision management,
first-class REFERENCE_ONLY linkages, and authorized binary streaming.
Enforces RBAC and Pertamina area scoping.
"""

from __future__ import annotations

import io
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response, StreamingResponse

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.drawing_file_validator import (
    DrawingFileTooLargeError,
    DrawingSignatureMismatchError,
    DrawingValidationError,
    InvalidDrawingExtensionError,
)
from API.drawing_service import DrawingConflictError, DrawingNotFoundError
from API.pump_area_scope import is_area_in_scope, resolve_asset_area
from dependencies import (
    get_current_user,
    get_drawing_repository,
    get_drawing_service,
    get_pump_gateway,
    get_seal_pump_compatibility_gateway,
    require_permission,
)
from models.responses import Payload

router = APIRouter(prefix="/api/ltsa/drawings", tags=["drawings"])


def _is_seal_in_scope(
    seal_code: str,
    scope: frozenset[str],
    seal_pump_compatibility_gateway,
    pump_gateway,
    area_cache: dict[str, str | None],
) -> bool:
    try:
        response = seal_pump_compatibility_gateway.list_seal_pump_compatibilities()
        rows = response.get("data") if isinstance(response, dict) else None
        if not isinstance(rows, list):
            return False
        for row in rows:
            if row.get("seal_code") == seal_code:
                tag = row.get("pump_tag_number")
                if tag:
                    if tag not in area_cache:
                        area_cache[tag] = resolve_asset_area(tag, pump_gateway)
                    if is_area_in_scope(area_cache[tag], scope):
                        return True
    except Exception:
        return False
    return False


def _is_drawing_in_scope(
    drawing: dict[str, Any],
    scope: frozenset[str],
    drawing_repository,
    pump_gateway,
    seal_pump_compatibility_gateway,
) -> bool:
    doc_code = drawing.get("document_code")
    dwg_no = drawing.get("document_number")
    links: list[dict[str, Any]] = []
    if doc_code:
        links.extend(drawing_repository.list_links_for_document(doc_code))
    if dwg_no:
        links.extend(drawing_repository.list_links_for_drawing_number(dwg_no))

    direct_seal = drawing.get("seal_code")

    # Unlinked physical drawing with no equipment or seal -> fail closed for scoped users
    if not links and not direct_seal:
        return False

    area_cache: dict[str, str | None] = {}

    for link in links:
        t_type = link.get("target_type")
        t_code = link.get("target_code")
        if t_type == "PUMP" and t_code:
            if t_code not in area_cache:
                area_cache[t_code] = resolve_asset_area(t_code, pump_gateway)
            if is_area_in_scope(area_cache[t_code], scope):
                return True
        elif t_type == "SEAL" and t_code:
            if _is_seal_in_scope(t_code, scope, seal_pump_compatibility_gateway, pump_gateway, area_cache):
                return True

    if direct_seal:
        if _is_seal_in_scope(direct_seal, scope, seal_pump_compatibility_gateway, pump_gateway, area_cache):
            return True

    return False


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("drawing.upload"))],
)
async def upload_drawing(
    drawing_number: str = Form(...),
    title: str = Form(...),
    revision: str | None = Form(default=None),
    seal_code: str | None = Form(default=None),
    asset_code: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    drawing_service=Depends(get_drawing_service),
) -> Payload:
    file_bytes = await file.read()
    try:
        created = drawing_service.register_drawing(
            file_bytes=file_bytes,
            filename=file.filename or "upload.pdf",
            drawing_number=drawing_number,
            title=title,
            revision=revision,
            uploaded_by=current_user.user_id,
            seal_code=seal_code,
            asset_code=asset_code,
            provenance="MANUAL",
            is_revision_upload=False,
        )
    except (
        DrawingValidationError,
        InvalidDrawingExtensionError,
        DrawingSignatureMismatchError,
        DrawingFileTooLargeError,
    ) as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except DrawingConflictError as conf_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(conf_err))

    return {"data": created}


@router.get(
    "",
    dependencies=[Depends(require_permission("drawing.read"))],
)
def list_drawings(
    drawing_number: str | None = Query(default=None),
    seal_code: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    drawing_repository=Depends(get_drawing_repository),
    pump_gateway=Depends(get_pump_gateway),
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
) -> Payload:
    drawings = drawing_repository.list_documents(
        drawing_number=drawing_number,
        seal_code=seal_code,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    scope = resolve_area_scope(current_user)
    if scope is not None:
        filtered = [
            d
            for d in drawings
            if _is_drawing_in_scope(
                d,
                scope,
                drawing_repository,
                pump_gateway,
                seal_pump_compatibility_gateway,
            )
        ]
        return {"data": filtered, "count": len(filtered)}

    return {"data": drawings, "count": len(drawings)}


@router.get(
    "/{document_code}",
    dependencies=[Depends(require_permission("drawing.read"))],
)
def get_drawing_detail(
    document_code: str,
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    drawing_service=Depends(get_drawing_service),
    drawing_repository=Depends(get_drawing_repository),
    pump_gateway=Depends(get_pump_gateway),
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
) -> Payload:
    try:
        detail = drawing_service.get_drawing(document_code)
    except DrawingNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing document not found")

    scope = resolve_area_scope(current_user)
    if scope is not None and not _is_drawing_in_scope(
        detail,
        scope,
        drawing_repository,
        pump_gateway,
        seal_pump_compatibility_gateway,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing document not found")

    return {"data": detail}


@router.get(
    "/{document_code}/content",
    dependencies=[Depends(require_permission("drawing.read"))],
)
def get_drawing_content(
    document_code: str,
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    drawing_service=Depends(get_drawing_service),
    drawing_repository=Depends(get_drawing_repository),
    pump_gateway=Depends(get_pump_gateway),
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
):
    try:
        doc = drawing_repository.get_document_by_code(document_code)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing document not found")

        # Authorization/area scope check MUST occur BEFORE accessing the binary
        scope = resolve_area_scope(current_user)
        if scope is not None and not _is_drawing_in_scope(
            doc,
            scope,
            drawing_repository,
            pump_gateway,
            seal_pump_compatibility_gateway,
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing document not found")

        content_bytes, content_type, filename = drawing_service.get_drawing_content(document_code)
    except DrawingNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing document content not found")

    return StreamingResponse(
        io.BytesIO(content_bytes),
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post(
    "/{document_code}/revisions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("drawing.upload"))],
)
async def upload_drawing_revision(
    document_code: str,
    revision: str = Form(...),
    title: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    drawing_service=Depends(get_drawing_service),
    drawing_repository=Depends(get_drawing_repository),
) -> Payload:
    parent_doc = drawing_repository.get_document_by_code(document_code)
    if parent_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent drawing document not found")

    file_bytes = await file.read()
    dwg_number = parent_doc.get("document_number", "")
    dwg_title = title.strip() if title else parent_doc.get("title", "")

    try:
        created = drawing_service.register_drawing(
            file_bytes=file_bytes,
            filename=file.filename or f"{dwg_number}_rev{revision}.pdf",
            drawing_number=dwg_number,
            title=dwg_title,
            revision=revision,
            uploaded_by=current_user.user_id,
            seal_code=parent_doc.get("seal_code"),
            provenance="MANUAL",
            is_revision_upload=True,
        )
    except (
        DrawingValidationError,
        InvalidDrawingExtensionError,
        DrawingSignatureMismatchError,
        DrawingFileTooLargeError,
    ) as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except DrawingConflictError as conf_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(conf_err))

    return {"data": created}


@router.post(
    "/{document_code}/links",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("drawing.manage"))],
)
def create_drawing_link(
    document_code: str,
    target_type: str = Form(...),
    target_code: str = Form(...),
    evidence_method: str = Form(default="MANUAL_VERIFICATION"),
    notes: str | None = Form(default=None),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    drawing_service=Depends(get_drawing_service),
) -> Payload:
    if target_type not in ("SEAL", "PUMP", "INSTALLATION", "HISTORICAL_SERVICE"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid target_type: {target_type}",
        )

    try:
        link = drawing_service.link_drawing(
            document_code=document_code,
            target_type=target_type,
            target_code=target_code,
            evidence_method=evidence_method,
            created_by=current_user.user_id,
            notes=notes,
        )
    except DrawingNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing document not found")

    return {"data": link}

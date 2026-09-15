from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.engineering_drawing_repository import (
    ArtifactNotFound,
    ComponentNotFound,
    CrossDrawingRevision,
    DrawingNotFound,
    DuplicateActiveLink,
    DuplicatePrimaryArtifact,
    EngineeringDrawingRepository,
    InvalidLinkTarget,
    KnowledgeSourceNotFound,
    RevisionNotFound,
)
from dependencies import get_current_user, get_engineering_drawing_repository, require_permission
from models.responses import Payload

# MWO-LTSA-DRAWING-INPUT-R4 -- router-level "drawing.read" (the exact,
# already-real permission routers/document.py already gates on; not
# reusing "condition.read" since Drawing already has its own established
# permission string, held by every non-Pertamina-Viewer role). Write
# routes reuse "maintenance.write" -- the same LTSA-domain write
# permission ltsa_finding/condition_monitoring_measurement already use --
# no new permission string invented.
router = APIRouter(dependencies=[Depends(require_permission("drawing.read"))])


def _actor_id(current_user: AuthenticatedIdentity) -> str:
    return current_user.user_id


def _domain_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, (DrawingNotFound, RevisionNotFound, KnowledgeSourceNotFound, ArtifactNotFound, ComponentNotFound, InvalidLinkTarget)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (CrossDrawingRevision, DuplicateActiveLink, DuplicatePrimaryArtifact)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


# ---- request models ----


class DrawingCreateRequest(BaseModel):
    drawing_number: str | None = None
    title: str
    manufacturer: str | None = None
    drawing_type: str | None = None


class DrawingUpdateRequest(BaseModel):
    drawing_number: str | None = None
    title: str | None = None
    manufacturer: str | None = None
    drawing_type: str | None = None


class RevisionCreateRequest(BaseModel):
    revision: str | None = None
    revision_date: str | None = None
    verification_status: str = "DRAFT"
    supersedes_revision_code: str | None = None
    notes: str | None = None


class RevisionUpdateRequest(BaseModel):
    revision: str | None = None
    revision_date: str | None = None
    verification_status: str | None = None
    supersedes_revision_code: str | None = None
    notes: str | None = None


class ArtifactCreateRequest(BaseModel):
    knowledge_source_id: str
    artifact_class: str = "UNKNOWN"
    is_primary: bool = False
    derived_from_artifact_code: str | None = None
    verification_status: str = "DRAFT"


class ArtifactUpdateRequest(BaseModel):
    is_primary: bool | None = None
    verification_status: str | None = None


class LinkCreateRequest(BaseModel):
    target_type: str
    target_code: str
    relationship_type: str
    verification_status: str = "DRAFT"
    source_reference: str | None = None


class BomLineCreateRequest(BaseModel):
    item_position: str | None = None
    component_id: str | None = None
    component_description: str | None = None
    quantity: float | None = None
    material_or_specification: str | None = None
    notes: str | None = None


class BomLineUpdateRequest(BaseModel):
    item_position: str | None = None
    component_id: str | None = None
    component_description: str | None = None
    quantity: float | None = None
    material_or_specification: str | None = None
    notes: str | None = None


# ---- drawing ----


@router.get("/api/ltsa/engineering-drawings")
def list_engineering_drawings(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return repository.list_drawings(scope=resolve_area_scope(current_user), limit=limit, offset=offset)


@router.post("/api/ltsa/engineering-drawings", dependencies=[Depends(require_permission("maintenance.write"))])
def create_engineering_drawing(
    payload: DrawingCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    created = repository.create_drawing(
        drawing_number=payload.drawing_number, title=payload.title, manufacturer=payload.manufacturer,
        drawing_type=payload.drawing_type, created_by=_actor_id(current_user),
    )
    return {"success": True, "data": created}


@router.get("/api/ltsa/engineering-drawings/{drawing_code}")
def get_engineering_drawing(
    drawing_code: str,
    include_retracted_links: bool = Query(False),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    if not repository.is_drawing_in_scope(drawing_code, scope):
        raise HTTPException(status_code=404, detail="Drawing not found")
    detail = repository.get_drawing_detail(drawing_code, include_retracted_links=include_retracted_links)
    if detail is None:
        raise HTTPException(status_code=404, detail="Drawing not found")
    return {"success": True, "data": detail}


@router.patch("/api/ltsa/engineering-drawings/{drawing_code}", dependencies=[Depends(require_permission("maintenance.write"))])
def update_engineering_drawing(
    drawing_code: str,
    payload: DrawingUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    updated = repository.update_drawing(drawing_code, values=payload.model_dump(exclude_unset=True), updated_by=_actor_id(current_user))
    if updated is None:
        raise HTTPException(status_code=404, detail="Drawing not found")
    return {"success": True, "data": updated}


@router.post(
    "/api/ltsa/engineering-drawings/{drawing_code}/current-revision/{revision_code}",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def set_engineering_drawing_current_revision(
    drawing_code: str,
    revision_code: str,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    try:
        updated = repository.set_current_revision(drawing_code, revision_code, updated_by=_actor_id(current_user))
    except (RevisionNotFound, CrossDrawingRevision) as exc:
        raise _domain_error_to_http(exc)
    if updated is None:
        raise HTTPException(status_code=404, detail="Drawing not found")
    return {"success": True, "data": updated}


# ---- revision ----


@router.get("/api/ltsa/engineering-drawings/{drawing_code}/revisions")
def list_engineering_drawing_revisions(
    drawing_code: str,
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    if not repository.is_drawing_in_scope(drawing_code, resolve_area_scope(current_user)):
        raise HTTPException(status_code=404, detail="Drawing not found")
    rows = repository.list_revisions_for_drawing(drawing_code)
    if rows is None:
        raise HTTPException(status_code=404, detail="Drawing not found")
    return {"success": True, "data": rows}


@router.post(
    "/api/ltsa/engineering-drawings/{drawing_code}/revisions",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_engineering_drawing_revision(
    drawing_code: str,
    payload: RevisionCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    try:
        created = repository.create_revision(
            drawing_code=drawing_code, revision=payload.revision, revision_date=payload.revision_date,
            verification_status=payload.verification_status, supersedes_revision_code=payload.supersedes_revision_code,
            notes=payload.notes, created_by=_actor_id(current_user),
        )
    except (DrawingNotFound, RevisionNotFound, CrossDrawingRevision, ValueError) as exc:
        raise _domain_error_to_http(exc)
    return {"success": True, "data": created}


def _drawing_code_for_revision(repository: EngineeringDrawingRepository, revision_code: str) -> str | None:
    revision = repository.find_revision(revision_code)
    return revision["drawing_code"] if revision else None


@router.get("/api/ltsa/engineering-drawing-revisions/{revision_code}")
def get_engineering_drawing_revision(
    revision_code: str,
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    revision = repository.find_revision(revision_code)
    if revision is None:
        raise HTTPException(status_code=404, detail="Revision not found")
    if not repository.is_drawing_in_scope(revision["drawing_code"], resolve_area_scope(current_user)):
        raise HTTPException(status_code=404, detail="Revision not found")
    return {"success": True, "data": revision}


@router.patch(
    "/api/ltsa/engineering-drawing-revisions/{revision_code}",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def update_engineering_drawing_revision(
    revision_code: str,
    payload: RevisionUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    try:
        updated = repository.update_revision(revision_code, values=payload.model_dump(exclude_unset=True), updated_by=_actor_id(current_user))
    except (RevisionNotFound, CrossDrawingRevision, ValueError) as exc:
        raise _domain_error_to_http(exc)
    if updated is None:
        raise HTTPException(status_code=404, detail="Revision not found")
    return {"success": True, "data": updated}


# ---- artifact ----


@router.get("/api/ltsa/engineering-drawing-revisions/{revision_code}/artifacts")
def list_engineering_drawing_artifacts(
    revision_code: str,
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    drawing_code = _drawing_code_for_revision(repository, revision_code)
    if drawing_code is None or not repository.is_drawing_in_scope(drawing_code, resolve_area_scope(current_user)):
        raise HTTPException(status_code=404, detail="Revision not found")
    rows = repository.list_artifacts_for_revision(revision_code)
    if rows is None:
        raise HTTPException(status_code=404, detail="Revision not found")
    return {"success": True, "data": rows}


@router.post(
    "/api/ltsa/engineering-drawing-revisions/{revision_code}/artifacts",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_engineering_drawing_artifact(
    revision_code: str,
    payload: ArtifactCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    try:
        created = repository.create_artifact(
            revision_code=revision_code, knowledge_source_id=payload.knowledge_source_id,
            artifact_class=payload.artifact_class, is_primary=payload.is_primary,
            derived_from_artifact_code=payload.derived_from_artifact_code,
            verification_status=payload.verification_status, created_by=_actor_id(current_user),
        )
    except (RevisionNotFound, KnowledgeSourceNotFound, ArtifactNotFound, DuplicatePrimaryArtifact, ValueError) as exc:
        raise _domain_error_to_http(exc)
    return {"success": True, "data": created}


def _drawing_code_for_artifact(repository: EngineeringDrawingRepository, artifact_code: str) -> str | None:
    artifact = repository.find_artifact(artifact_code)
    if artifact is None:
        return None
    return _drawing_code_for_revision(repository, artifact["revision_code"])


@router.get("/api/ltsa/engineering-drawing-artifacts/{artifact_code}")
def get_engineering_drawing_artifact(
    artifact_code: str,
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    artifact = repository.find_artifact(artifact_code)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    drawing_code = _drawing_code_for_revision(repository, artifact["revision_code"])
    if drawing_code is None or not repository.is_drawing_in_scope(drawing_code, resolve_area_scope(current_user)):
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"success": True, "data": artifact}


@router.patch(
    "/api/ltsa/engineering-drawing-artifacts/{artifact_code}",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def update_engineering_drawing_artifact(
    artifact_code: str,
    payload: ArtifactUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    try:
        updated = repository.update_artifact(artifact_code, values=payload.model_dump(exclude_unset=True), updated_by=_actor_id(current_user))
    except (DuplicatePrimaryArtifact, ValueError) as exc:
        raise _domain_error_to_http(exc)
    if updated is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"success": True, "data": updated}


# ---- link ----


@router.get("/api/ltsa/engineering-drawings/{drawing_code}/links")
def list_engineering_drawing_links(
    drawing_code: str,
    include_retracted: bool = Query(False),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    if not repository.is_drawing_in_scope(drawing_code, resolve_area_scope(current_user)):
        raise HTTPException(status_code=404, detail="Drawing not found")
    rows = repository.list_links_for_drawing(drawing_code, include_retracted=include_retracted)
    if rows is None:
        raise HTTPException(status_code=404, detail="Drawing not found")
    return {"success": True, "data": rows}


@router.post(
    "/api/ltsa/engineering-drawings/{drawing_code}/links",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_engineering_drawing_link(
    drawing_code: str,
    payload: LinkCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    try:
        created = repository.create_link(
            drawing_code=drawing_code, target_type=payload.target_type, target_code=payload.target_code,
            relationship_type=payload.relationship_type, verification_status=payload.verification_status,
            source_reference=payload.source_reference, created_by=_actor_id(current_user),
        )
    except (DrawingNotFound, InvalidLinkTarget, DuplicateActiveLink, ValueError) as exc:
        raise _domain_error_to_http(exc)
    return {"success": True, "data": created}


@router.post(
    "/api/ltsa/engineering-drawing-links/{link_code}/retract",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def retract_engineering_drawing_link(
    link_code: str,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    # Never a hard-delete route -- retract only, per R4 Section 8.
    updated = repository.retract_link(link_code, retracted_by=_actor_id(current_user))
    if updated is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"success": True, "data": updated}


# ---- BOM ----


@router.get("/api/ltsa/engineering-drawing-revisions/{revision_code}/bom")
def list_engineering_drawing_bom(
    revision_code: str,
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    drawing_code = _drawing_code_for_revision(repository, revision_code)
    if drawing_code is None or not repository.is_drawing_in_scope(drawing_code, resolve_area_scope(current_user)):
        raise HTTPException(status_code=404, detail="Revision not found")
    rows = repository.list_bom_for_revision(revision_code)
    if rows is None:
        raise HTTPException(status_code=404, detail="Revision not found")
    return {"success": True, "data": rows}


@router.post(
    "/api/ltsa/engineering-drawing-revisions/{revision_code}/bom",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_engineering_drawing_bom_line(
    revision_code: str,
    payload: BomLineCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    try:
        created = repository.create_bom_line(
            revision_code=revision_code, item_position=payload.item_position, component_id=payload.component_id,
            component_description=payload.component_description, quantity=payload.quantity,
            material_or_specification=payload.material_or_specification, notes=payload.notes,
            created_by=_actor_id(current_user),
        )
    except (RevisionNotFound, ComponentNotFound) as exc:
        raise _domain_error_to_http(exc)
    return {"success": True, "data": created}


@router.get("/api/ltsa/engineering-drawing-bom/{bom_line_code}")
def get_engineering_drawing_bom_line(
    bom_line_code: str,
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    bom_line = repository.find_bom_line(bom_line_code)
    if bom_line is None:
        raise HTTPException(status_code=404, detail="BOM line not found")
    drawing_code = _drawing_code_for_revision(repository, bom_line["revision_code"])
    if drawing_code is None or not repository.is_drawing_in_scope(drawing_code, resolve_area_scope(current_user)):
        raise HTTPException(status_code=404, detail="BOM line not found")
    return {"success": True, "data": bom_line}


@router.patch(
    "/api/ltsa/engineering-drawing-bom/{bom_line_code}",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def update_engineering_drawing_bom_line(
    bom_line_code: str,
    payload: BomLineUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: EngineeringDrawingRepository = Depends(get_engineering_drawing_repository),
) -> Payload:
    try:
        updated = repository.update_bom_line(bom_line_code, values=payload.model_dump(exclude_unset=True), updated_by=_actor_id(current_user))
    except ComponentNotFound as exc:
        raise _domain_error_to_http(exc)
    if updated is None:
        raise HTTPException(status_code=404, detail="BOM line not found")
    return {"success": True, "data": updated}

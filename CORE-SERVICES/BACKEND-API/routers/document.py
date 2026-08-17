from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_seal_engineering_document_gateway, require_permission
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("drawing.read"))])

# Document Workspace API (MWO-LTSA-062, Document & Drawing Productionization)
# -- reuses SealEngineeringDocumentGateway unmodified (built under
# MWO-LTSA-030/040B, already exposed via list_seal_engineering_documents(),
# already the real data source Drawing Workspace's own knowledge-endpoint
# path filters down to document_type == 'DRAWING'). This is the first
# router to expose the gateway's list() directly -- it was constructed in
# dependencies.py from the start but never wired into a router (confirmed
# gap, MWO-LTSA-060's own archaeology). No new gateway, service,
# repository, or workflow -- only the router layer was missing, mirroring
# seal.py's identical pass-through shape.
#
# Returns EVERY seal_engineering_document row (all seven document_type
# values, not just DRAWING) -- Document Workspace filters/groups
# client-side (documentMapping.js), the same way Seal.jsx/Pump.jsx already
# filter their own full-list responses. Drawing Workspace also reuses this
# same endpoint (not a second one) to resolve its own Document/Seal
# relationships -- see drawingMapping.js's own header comment for why.


@router.get("/api/ltsa/documents")
def list_ltsa_documents(
    seal_engineering_document_gateway=Depends(get_seal_engineering_document_gateway),
) -> Payload:
    return seal_engineering_document_gateway.list_seal_engineering_documents()

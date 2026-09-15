from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from API.STREAMING.live_stream_api import LiveStreamAPI
from API.workforce_service import WorkforceService
from dependencies import (
    get_copilot_ai_client,
    get_live_stream_api,
    get_workforce_service,
)
from WORKFORCE.approval_chain_runtime import (
    ChiefApprovalRecord,
    ChiefApprovalRequiredError,
)

router = APIRouter(tags=["workforce"])


class TaskAssignRequest(BaseModel):
    title: str = Field(..., description="Task or work item title")
    description: str = Field(default="", description="Detailed work description")
    position_id: str | None = Field(default=None, description="Target position ID (e.g. CTO, BACKEND_ENGINEER)")
    employee_id: str | None = Field(default=None, description="Target digital employee ID")
    is_production: bool = Field(default=False, description="Whether this task has production impact requiring Chief approval")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")


class WorkforceChatRequest(BaseModel):
    employee_id: str = Field(..., description="Digital employee ID or position ID to chat with")
    message: str = Field(..., description="Message or instruction for the digital employee")
    conversation_id: str | None = Field(default=None, description="Existing conversation thread ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")


class TaskReleaseRequest(BaseModel):
    approver_id: str | None = None
    approver_role: str | None = None
    is_human: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/api/workforce/employees")
def list_employees(
    workforce_service: WorkforceService = Depends(get_workforce_service),
) -> list[dict[str, Any]]:
    """List all digital employees in the workforce with roles, status, skills, and current tasks."""
    return workforce_service.list_employees()


@router.get("/api/workforce/employees/{employee_id}")
def get_employee(
    employee_id: str,
    workforce_service: WorkforceService = Depends(get_workforce_service),
) -> dict[str, Any]:
    """Get single digital employee details, active task, and recent activity history."""
    employee = workforce_service.get_employee(employee_id)
    if employee is None:
        raise HTTPException(
            status_code=404,
            detail=f"Employee not found: {employee_id}",
        )
    return employee


@router.get("/api/workforce/board")
def get_board(
    workforce_service: WorkforceService = Depends(get_workforce_service),
) -> dict[str, Any]:
    """Get the current state of the workforce board (published, claimed, completed, released)."""
    return workforce_service.get_board()


@router.get("/api/workforce/activities")
def list_activities(
    employee_id: str | None = Query(default=None, description="Filter activities by employee ID"),
    limit: int = Query(default=50, ge=1, le=500, description="Max activities to return"),
    workforce_service: WorkforceService = Depends(get_workforce_service),
) -> list[dict[str, Any]]:
    """Get the digital workforce activity feed."""
    return workforce_service.list_activities(employee_id=employee_id, limit=limit)


@router.get("/api/workforce/metrics")
def get_metrics(
    workforce_service: WorkforceService = Depends(get_workforce_service),
) -> dict[str, Any]:
    """Get workforce operational, status, and task completion metrics."""
    return workforce_service.get_metrics()


@router.post("/api/workforce/tasks/assign")
def assign_task(
    payload: TaskAssignRequest,
    workforce_service: WorkforceService = Depends(get_workforce_service),
) -> dict[str, Any]:
    """Assign or publish a new task to the digital workforce."""
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Task title is required")

    try:
        return workforce_service.assign_task(
            title=payload.title,
            description=payload.description,
            position_id=payload.position_id,
            employee_id=payload.employee_id,
            is_production=payload.is_production,
            metadata=payload.metadata,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/workforce/tasks/{work_item_id}/release")
def release_task(
    work_item_id: str,
    payload: TaskReleaseRequest | None = None,
    workforce_service: WorkforceService = Depends(get_workforce_service),
) -> dict[str, Any]:
    """Release a completed task, enforcing the Human Chief Approval Gate for production tasks."""
    approval_record = None
    if payload and payload.approver_id and payload.approver_role:
        approval_record = ChiefApprovalRecord(
            work_item_id=work_item_id,
            approver_id=payload.approver_id,
            approver_role=payload.approver_role,
            is_human=bool(payload.is_human),
            metadata=payload.metadata,
        )

    try:
        released_item = workforce_service.release_task(
            work_item_id=work_item_id,
            approval=approval_record,
        )
        return {
            "status": "RELEASED",
            "work_item": workforce_service.serialize_work_item(released_item),
        }
    except ChiefApprovalRequiredError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/workforce/chat")
def workforce_chat(
    payload: WorkforceChatRequest,
    workforce_service: WorkforceService = Depends(get_workforce_service),
    ai_client=Depends(get_copilot_ai_client),
) -> dict[str, Any]:
    """Chat with an AI digital employee using conversation store and engineering AI router."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        return workforce_service.chat(
            employee_id=payload.employee_id,
            message=payload.message,
            conversation_id=payload.conversation_id,
            ai_client=ai_client,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/api/studio/events/stream")
async def stream_studio_events(
    request: Request,
    live_stream_api: LiveStreamAPI = Depends(get_live_stream_api),
    limit: int = Query(default=50, ge=0, le=500),
    follow: bool = Query(default=True, description="Keep streaming events in realtime"),
) -> StreamingResponse:
    """Mount point for Studio Server-Sent Events (SSE) stream consumed by AI5R Studio."""
    queue: asyncio.Queue = asyncio.Queue()
    live_stream_api.add_subscriber(queue)

    async def event_generator():
        try:
            # Yield initial bounded recent events
            for chunk in live_stream_api.sse(limit=limit):
                yield chunk

            if not follow:
                return

            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield live_stream_api._to_sse(event)
                except asyncio.TimeoutError:
                    # Keep-alive SSE comment to prevent proxy/browser timeout
                    yield ": keepalive\n\n"
        finally:
            live_stream_api.remove_subscriber(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


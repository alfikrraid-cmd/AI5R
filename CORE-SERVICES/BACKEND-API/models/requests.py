from __future__ import annotations

from pydantic import BaseModel

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

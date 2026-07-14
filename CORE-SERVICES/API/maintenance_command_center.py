from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .maintenance_history_gateway import MaintenanceHistoryGateway
from .organization_registry import get_organization
from .pump_gateway import PumpGateway
from .work_order_gateway import WorkOrderGateway

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]

RECENT_LIMIT = 5


def get_maintenance_command_center(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    today: date | None = None,
    pump_gateway: PumpGateway | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
) -> dict[str, Any]:
    """The Maintenance Command Center: a read-only presentation of the
    existing Pump Gateway, Work Order Gateway, Maintenance History Gateway,
    and Organization Registry. Manufactures nothing, persists nothing,
    modifies nothing.
    """

    pump_gateway = pump_gateway or PumpGateway()
    work_order_gateway = work_order_gateway or WorkOrderGateway()
    maintenance_history_gateway = maintenance_history_gateway or MaintenanceHistoryGateway()
    today = today or date.today()

    pumps = pump_gateway.list_pumps().get("data") or []
    work_orders = work_order_gateway.list_work_orders().get("data") or []
    maintenance_history = maintenance_history_gateway.list_maintenance_history().get("data") or []
    organization = get_organization(product_name, root_path)

    active_work_orders = [wo for wo in work_orders if not wo.get("closed_at")]
    completed_today = [
        record
        for record in maintenance_history
        if str(record.get("performed_at") or "")[:10] == today.isoformat()
    ]

    return {
        "summary": {
            "total_pumps": len(pumps),
            "active_work_orders": len(active_work_orders),
            "completed_today": len(completed_today),
            # No due-date/deadline field exists anywhere in the canonical
            # Work Order schema (work_order_code, customer_code, asset_code,
            # asset_type, description, priority, status, assigned_to,
            # created_at, updated_at, closed_at) or its Gateway, so
            # "overdue" cannot be computed from reused data without
            # inventing a new business rule. Reported as 0, not derived.
            "overdue_work_orders": 0,
        },
        "recent_work_orders": [
            {
                "work_order_code": wo.get("work_order_code"),
                "pump": wo.get("asset_code"),
                "assigned_role": wo.get("assigned_to"),
                "status": wo.get("status"),
            }
            for wo in work_orders[:RECENT_LIMIT]
        ],
        "recent_maintenance": [
            {
                "maintenance_code": record.get("maintenance_record_code"),
                "pump": record.get("asset_code"),
                "completed_by": record.get("performed_by"),
                "completed_time": record.get("performed_at"),
            }
            for record in maintenance_history[:RECENT_LIMIT]
        ],
        "organization_summary": {
            "departments": len(organization["departments"]),
            "roles": len(organization["roles"]),
        },
    }

from __future__ import annotations

from pathlib import Path
from typing import Any

from .maintenance_history_gateway import MaintenanceHistoryGateway
from .pump_gateway import PumpGateway
from .role_manufacturing import retrieve_role_artifact
from .work_order_gateway import WorkOrderGateway

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def execute_maintenance(
    *,
    product_name: str,
    tag_number: str,
    work_order_code: str,
    maintenance_record_code: str,
    description: str,
    action_taken: str,
    role_name: str | None = None,
    priority: str = "NORMAL",
    performed_by: str | None = None,
    notes: str | None = None,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    pump_gateway: PumpGateway | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
) -> dict[str, Any]:
    """The Maintenance Execution Runtime: orchestrates the existing Pump
    Gateway, Work Order Gateway, Maintenance History Gateway, and Role
    Manufacturing into one business flow.

    Retrieve Pump -> Create Work Order -> Assign Role ->
    Create Maintenance History -> Return Runtime Result.

    No manufacturing, no persistence, no gateway or registry changes.
    """

    pump_gateway = pump_gateway or PumpGateway()
    work_order_gateway = work_order_gateway or WorkOrderGateway()
    maintenance_history_gateway = maintenance_history_gateway or MaintenanceHistoryGateway()

    pump_response = pump_gateway.get_pump(tag_number)

    if not pump_response.get("success"):
        return {
            "success": False,
            "step": "RETRIEVE_PUMP",
            "pump": pump_response,
            "role": None,
            "work_order": None,
            "maintenance_history": None,
        }

    pump = pump_response["data"]

    role = None
    if role_name:
        role = retrieve_role_artifact(product_name, role_name, root_path)

    work_order_response = work_order_gateway.create_work_order(
        {
            "work_order_code": work_order_code,
            "asset_code": pump.get("tag_number"),
            "asset_type": pump.get("pump_type"),
            "description": description,
            "priority": priority,
            "assigned_to": role_name,
        }
    )

    if not work_order_response.get("success"):
        return {
            "success": False,
            "step": "CREATE_WORK_ORDER",
            "pump": pump_response,
            "role": role,
            "work_order": work_order_response,
            "maintenance_history": None,
        }

    maintenance_history_response = maintenance_history_gateway.create_maintenance_history(
        {
            "maintenance_record_code": maintenance_record_code,
            "work_order_code": work_order_code,
            "asset_code": pump.get("tag_number"),
            "asset_type": pump.get("pump_type"),
            "action_taken": action_taken,
            "performed_by": performed_by,
            "notes": notes,
        }
    )

    if not maintenance_history_response.get("success"):
        return {
            "success": False,
            "step": "CREATE_MAINTENANCE_HISTORY",
            "pump": pump_response,
            "role": role,
            "work_order": work_order_response,
            "maintenance_history": maintenance_history_response,
        }

    return {
        "success": True,
        "step": "COMPLETE",
        "pump": pump_response,
        "role": role,
        "work_order": work_order_response,
        "maintenance_history": maintenance_history_response,
    }

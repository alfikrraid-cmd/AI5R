from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .maintenance_command_center import get_maintenance_command_center
from .maintenance_history_gateway import MaintenanceHistoryGateway
from .pump_gateway import PumpGateway
from .role_manufacturing import retrieve_role_artifact
from .work_order_gateway import WorkOrderGateway

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def get_pump_status(
    tag_number: str,
    pump_gateway: PumpGateway | None = None,
) -> dict[str, Any]:
    """Show Pump Status: the pump's current detail, unchanged, via Pump
    Gateway."""

    pump_gateway = pump_gateway or PumpGateway()

    return pump_gateway.get_pump(tag_number)


def get_pump_history(
    tag_number: str,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
) -> dict[str, Any]:
    """Show Pump History: maintenance history records for one pump,
    filtered from Maintenance History Gateway's existing list."""

    maintenance_history_gateway = maintenance_history_gateway or MaintenanceHistoryGateway()
    response = maintenance_history_gateway.list_maintenance_history()
    records = [
        record
        for record in (response.get("data") or [])
        if record.get("asset_code") == tag_number
    ]

    return {
        "success": response.get("success", False),
        "tag_number": tag_number,
        "records": records,
    }


def get_active_work_orders(
    tag_number: str | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
) -> dict[str, Any]:
    """Show Active Work Orders: open work orders from Work Order Gateway's
    existing list, optionally narrowed to one pump."""

    work_order_gateway = work_order_gateway or WorkOrderGateway()
    response = work_order_gateway.list_work_orders()
    work_orders = [wo for wo in (response.get("data") or []) if not wo.get("closed_at")]

    if tag_number:
        work_orders = [wo for wo in work_orders if wo.get("asset_code") == tag_number]

    return {
        "success": response.get("success", False),
        "work_orders": work_orders,
    }


def get_assigned_role(
    product_name: str,
    work_order_code: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    work_order_gateway: WorkOrderGateway | None = None,
) -> dict[str, Any] | None:
    """Show Assigned Role: the Role artifact assigned to a work order, via
    Work Order Gateway's detail and Organization Registry."""

    work_order_gateway = work_order_gateway or WorkOrderGateway()
    response = work_order_gateway.get_work_order(work_order_code)

    if not response.get("success"):
        return None

    role_name = (response.get("data") or {}).get("assigned_to")

    if not role_name:
        return None

    return retrieve_role_artifact(product_name, role_name, root_path)


def get_recent_maintenance(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    today: date | None = None,
    pump_gateway: PumpGateway | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
) -> list[dict[str, Any]]:
    """Show Recent Maintenance: reused unchanged from the Maintenance
    Command Center's already-computed recent maintenance list."""

    command_center = get_maintenance_command_center(
        product_name,
        root_path=root_path,
        today=today,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    return command_center["recent_maintenance"]


def summarize_situation(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    today: date | None = None,
    pump_gateway: PumpGateway | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
) -> dict[str, Any]:
    """Summarize Current Situation: reused unchanged from the Maintenance
    Command Center."""

    return get_maintenance_command_center(
        product_name,
        root_path=root_path,
        today=today,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

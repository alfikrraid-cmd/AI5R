from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .maintenance_intelligence_service import (
    get_active_work_orders,
    get_assigned_role,
    get_pump_history,
    get_pump_status,
    summarize_situation,
)

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def show_pump(tag_number: str) -> dict[str, Any]:
    """Show Pump: presents a pump's current detail from Maintenance
    Intelligence Service."""

    status = get_pump_status(tag_number)
    pump = status.get("data")

    if not status.get("success") or not pump:
        return {"message": f"Pump {tag_number} was not found.", "data": status}

    return {
        "message": (
            f"Pump {pump.get('tag_number', tag_number)} "
            f"({pump.get('pump_type', 'unknown type')}) — status: "
            f"{pump.get('status', 'UNKNOWN')}."
        ),
        "data": status,
    }


def explain_pump_status(tag_number: str) -> dict[str, Any]:
    """Explain Pump Status: a plain-language explanation of a pump's
    current status from Maintenance Intelligence Service."""

    status = get_pump_status(tag_number)
    pump = status.get("data")

    if not status.get("success") or not pump:
        return {"message": f"Pump {tag_number} was not found.", "data": status}

    return {
        "message": (
            f"Pump {pump.get('tag_number', tag_number)} is currently "
            f"{pump.get('status', 'UNKNOWN')}, located at "
            f"{pump.get('location') or 'an unknown location'} in area "
            f"{pump.get('area') or 'an unknown area'}."
        ),
        "data": status,
    }


def explain_pump_history(tag_number: str) -> dict[str, Any]:
    """Explain Pump History: a plain-language explanation of a pump's
    maintenance history from Maintenance Intelligence Service."""

    history = get_pump_history(tag_number)
    records = history.get("records") or []

    if not records:
        return {
            "message": f"No maintenance history found for pump {tag_number}.",
            "data": history,
        }

    lines = [
        f"- {record.get('maintenance_record_code')}: {record.get('action_taken')} "
        f"by {record.get('performed_by') or 'unknown'} on "
        f"{record.get('performed_at') or 'an unknown date'}"
        for record in records
    ]

    return {
        "message": (
            f"Pump {tag_number} has {len(records)} maintenance record(s):\n" + "\n".join(lines)
        ),
        "data": history,
    }


def explain_work_orders(tag_number: str | None = None) -> dict[str, Any]:
    """Explain Work Orders: a plain-language explanation of active work
    orders from Maintenance Intelligence Service, optionally scoped to one
    pump."""

    result = get_active_work_orders(tag_number)
    work_orders = result.get("work_orders") or []
    scope = f" for pump {tag_number}" if tag_number else ""

    if not work_orders:
        return {"message": f"No active work orders{scope}.", "data": result}

    lines = [
        f"- {wo.get('work_order_code')}: {wo.get('status') or 'OPEN'} "
        f"(assigned to {wo.get('assigned_to') or 'nobody'})"
        for wo in work_orders
    ]

    return {
        "message": (
            f"{len(work_orders)} active work order(s){scope}:\n" + "\n".join(lines)
        ),
        "data": result,
    }


def explain_assigned_role(
    product_name: str,
    work_order_code: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    """Explain Assigned Roles: a plain-language explanation of the Role
    assigned to a work order, from Maintenance Intelligence Service."""

    role = get_assigned_role(product_name, work_order_code, root_path=root_path)

    if role is None:
        return {
            "message": f"Work order {work_order_code} has no role assigned.",
            "data": None,
        }

    role_name = role["role"]["name"]
    department = role["relationships"]["department"]

    return {
        "message": f"Work order {work_order_code} is assigned to {role_name} in {department}.",
        "data": role,
    }


def summarize_maintenance_situation(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    today: date | None = None,
    scope: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Summarize Maintenance Situation: a plain-language summary of the
    current maintenance situation from Maintenance Intelligence Service."""

    situation = summarize_situation(product_name, root_path=root_path, today=today, scope=scope)
    summary = situation["summary"]

    message = (
        f"{summary['total_pumps']} pump(s) tracked, "
        f"{summary['active_work_orders']} active work order(s), "
        f"{summary['completed_today']} maintenance record(s) completed today, "
        f"{summary['overdue_work_orders']} overdue work order(s)."
    )

    return {"message": message, "data": situation}

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_API_DIR = Path(__file__).resolve().parent
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
AI5R_SDK_DIR = CORE_SERVICES_DIR.parent / "AI5R-SDK"

for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR, AI5R_SDK_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from API.maintenance_history_gateway import MaintenanceHistoryGateway
from API.pump_gateway import PumpGateway
from API.work_order_gateway import WorkOrderGateway

PRODUCT_NAME = os.getenv("AI5R_PRODUCT_NAME", "LTSA-BRAIN")

_pump_gateway = PumpGateway()
_work_order_gateway = WorkOrderGateway()
_maintenance_history_gateway = MaintenanceHistoryGateway()


def get_product_name() -> str:
    return PRODUCT_NAME


def get_pump_gateway() -> PumpGateway:
    return _pump_gateway


def get_work_order_gateway() -> WorkOrderGateway:
    return _work_order_gateway


def get_maintenance_history_gateway() -> MaintenanceHistoryGateway:
    return _maintenance_history_gateway

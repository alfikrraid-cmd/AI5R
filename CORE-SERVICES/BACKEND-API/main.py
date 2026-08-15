from __future__ import annotations

import sys
from pathlib import Path

BACKEND_API_DIR = Path(__file__).resolve().parent
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
AI5R_SDK_DIR = CORE_SERVICES_DIR.parent / "AI5R-SDK"

for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR, AI5R_SDK_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from fastapi import FastAPI

from routers import copilot, dashboard, health, maintenance, organization, pumps, seal, work_orders

app = FastAPI(
    title="AI5R Enterprise OS Backend API",
    version="1.0.0",
    description=(
        "Integration layer only: every endpoint delegates to an already-"
        "approved Enterprise OS module (Company/Department/Role "
        "Manufacturing, Organization Registry, Organization Dashboard, the "
        "Pump/Seal/Work Order/Maintenance History Gateways, and the "
        "Maintenance Copilot). No business logic lives here."
    ),
)

app.include_router(health.router)
app.include_router(organization.router)
app.include_router(dashboard.router)
app.include_router(pumps.router)
app.include_router(seal.router)
app.include_router(work_orders.router)
app.include_router(maintenance.router)
app.include_router(copilot.router)

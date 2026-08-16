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

from API.auth_service import signing_secret
from routers import auth, copilot, dashboard, health, import_router, maintenance, organization, pumps, seal, work_orders

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


# MWO-LTSA-AUTH-001 -- "Fail startup clearly if production auth
# configuration is unsafe or missing." signing_secret() itself already
# raises AuthConfigurationError when AI5R_ENV=production and no
# AI5R_AUTH_JWT_SECRET is set; calling it once here, at import time
# (before uvicorn ever accepts a connection), turns that into a real
# startup failure instead of a lazy failure on the first login request.
# A no-op in dev/test (AI5R_ENV unset or != production).
signing_secret()

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organization.router)
app.include_router(dashboard.router)
app.include_router(pumps.router)
app.include_router(seal.router)
app.include_router(work_orders.router)
app.include_router(maintenance.router)
app.include_router(copilot.router)
app.include_router(import_router.router)

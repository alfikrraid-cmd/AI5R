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
from routers import (
    admin_users,
    auth,
    cm_report,
    condition_monitoring,
    copilot,
    dashboard,
    document,
    fleet,
    health,
    import_router,
    installation,
    maintenance,
    organization,
    pm_occurrence,
    pm_schedule,
    pumps,
    seal,
    work_orders,
)

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
# MWO-LTSA-AUTH-003A-FINAL -- User Administration. Every route requires
# admin.users (get_current_user is the router's own module-level
# dependency; per-route _require_admin_users()/authorize_user_management()
# enforce the specific permission + delegation scope).
app.include_router(admin_users.router)
app.include_router(organization.router)
app.include_router(dashboard.router)
app.include_router(pumps.router)
app.include_router(seal.router)
app.include_router(work_orders.router)
app.include_router(maintenance.router)
app.include_router(copilot.router)
app.include_router(import_router.router)

# MWO-LTSA-AUTH-001A -- these 7 routers were fully implemented, tested, and
# already permission-gated (require_permission), but never registered here
# -- a pre-existing gap, not new work. Each depends only on already-
# constructed, real gateway singletons in dependencies.py (no placeholder/
# None pattern), unlike engineering_ai (see routers/engineering_ai.py --
# its orchestrator is never configured outside its own test file, so it
# stays unwired; wiring it now would expose a 500-on-every-request
# endpoint, not close a gap).
app.include_router(fleet.router)
app.include_router(document.router)
app.include_router(installation.router)
app.include_router(pm_schedule.router)
app.include_router(pm_occurrence.router)
app.include_router(cm_report.router)
app.include_router(condition_monitoring.router)

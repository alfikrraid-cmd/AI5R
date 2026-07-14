from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# Pass-through endpoints return exactly what the reused Enterprise OS module
# already returns. That shape is owned by the reused module (Organization
# Registry, Organization Dashboard, the Gateways, the Copilot) -- it is
# intentionally not re-declared as a field-by-field schema here, to avoid a
# second, drifting definition of a shape that already lives elsewhere.
Payload = dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str
    organization: str
    database: str
    n8n: str

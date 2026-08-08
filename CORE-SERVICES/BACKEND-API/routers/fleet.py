from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from API.fleet_insight import build_fleet_insight
from dependencies import get_fleet_executive_summary_service, get_fleet_reliability_service
from models.responses import Payload

router = APIRouter()

# MWO-LTSA-038C -- Power BI dataset contract version. Reuses the exact
# same constant-plus-isoformat-timestamp convention
# EngineeringContextEngine.CONTEXT_VERSION already established, not a new
# pattern. Bump this only when the /api/ltsa/fleet/powerbi response shape
# itself changes.
DATASET_VERSION = "1.0.0"

# Fleet Reliability API (MWO-LTSA-037C) -- exposes the already-built
# FleetReliabilityService (MWO-LTSA-037B) via one endpoint. Router only:
# no filtering, no derivation, no business logic here -- .build()'s own
# result is used unchanged, the same "reused shape, not redefined"
# discipline pumps.py's Knowledge endpoint already follows. One Aggregate
# (FleetReliabilityService), One API (this single route) -- no Bad Actor,
# Site KPI, or Trend endpoint here, since FleetReliabilityService itself
# does not compute them (explicitly out of MWO-LTSA-037B's own scope).


@router.get("/api/ltsa/fleet/reliability")
def get_fleet_reliability(
    fleet_reliability_service=Depends(get_fleet_reliability_service),
) -> Payload:
    fleet_reliability = fleet_reliability_service.build()

    return {
        "success": True,
        "data": dataclasses.asdict(fleet_reliability),
    }


# Power BI API (MWO-LTSA-038A) -- one endpoint, one fetch, exposing
# FleetExecutiveSummary (MWO-LTSA-037E) and FleetInsight (MWO-LTSA-037F)
# together. Router only: no filtering, no derivation -- .build()'s own
# result and build_fleet_insight()'s own pure field selection over that
# same result are used unchanged. FleetExecutiveSummaryService already
# reuses FleetReliabilityService internally (MWO-LTSA-037E), so this is
# still exactly one HTTP round trip for an external consumer (Power BI),
# never a second backend call for the insight.


@router.get("/api/ltsa/fleet/powerbi")
def get_fleet_powerbi(
    fleet_executive_summary_service=Depends(get_fleet_executive_summary_service),
) -> Payload:
    summary = fleet_executive_summary_service.build()
    insight = build_fleet_insight(summary)

    return {
        "success": True,
        # MWO-LTSA-038C -- dataset contract envelope metadata: describes
        # this response (which schema version, generated when), not fleet
        # data, so it sits alongside "data" (like get_ltsa_pump_knowledge's
        # own tag_number), never inside it. generated_at is computed fresh
        # on every request -- no scheduler, no refresh job, no cache.
        "dataset_version": DATASET_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": {
            **dataclasses.asdict(summary),
            "insight": dataclasses.asdict(insight) if insight is not None else None,
        },
    }

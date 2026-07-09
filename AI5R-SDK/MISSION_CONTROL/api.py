from typing import Any

from MISSION_CONTROL.projector import MissionControlProjector


class MissionControlAPI:
    def snapshot_from_demo_result(self, demo_result: dict[str, Any]) -> dict[str, Any]:
        projector = MissionControlProjector()

        for event in demo_result.get("activity_stream", []):
            projector.project(event)

        snapshot = projector.model.snapshot()

        return {
            "status": "MISSION_CONTROL_READY",
            "mission": {
                "name": "Build FastAPI Login API",
                "status": demo_result.get("status"),
            },
            "organization": snapshot["organization"],
            "timeline": snapshot["timeline"],
            "digital_twins": demo_result.get("digital_twin_snapshot", {}),
            "production_plan": demo_result.get("production_plan", {}),
            "artifacts": snapshot["artifacts"],
            "statistics": {
                "employees_active": len(snapshot["organization"]),
                "timeline_events": len(snapshot["timeline"]),
                "planned_artifacts": len(
                    demo_result.get("production_plan", {}).get("artifacts", [])
                ),
            },
        }

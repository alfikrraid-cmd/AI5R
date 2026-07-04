from datetime import datetime
from uuid import uuid4


class WorkOrderGenerator:
    """
    LTSA-010 Work Order Generator

    Convert maintenance decision into a work order object.
    """

    def generate(self, asset, decision):
        if not asset:
            raise ValueError("asset is required")

        if not decision:
            raise ValueError("decision is required")

        return {
            "work_order_id": str(uuid4()),
            "object_type": "work_order",
            "asset": asset,
            "decision": decision.get("decision"),
            "priority": decision.get("priority"),
            "reason": decision.get("reason"),
            "status": "OPEN",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "tasks": self._tasks_for(decision.get("decision")),
        }

    def _tasks_for(self, decision_name):
        if decision_name == "REPLACE_BEARING":
            return [
                "Isolate pump",
                "Inspect bearing housing",
                "Replace bearing",
                "Inspect mechanical seal",
                "Perform alignment inspection",
                "Run test after maintenance",
            ]

        if decision_name == "INSPECT_IMMEDIATELY":
            return [
                "Inspect pump condition",
                "Check vibration level",
                "Check temperature",
                "Check seal leakage",
                "Prepare maintenance recommendation",
            ]

        if decision_name == "SCHEDULE_INSPECTION":
            return [
                "Schedule inspection",
                "Monitor vibration",
                "Monitor bearing temperature",
                "Review inspection findings",
            ]

        return [
            "Assign engineer for manual review",
            "Review findings",
            "Determine corrective action",
        ]

class DecisionEngine:
    """
    LTSA-009 Decision Engine

    Convert recommendation output into a maintenance decision.
    """

    DECISIONS = {
        "CRITICAL": {
            "decision": "IMMEDIATE_MAINTENANCE_REQUIRED",
            "next_step": "Generate urgent work order",
            "execution_mode": "urgent",
        },
        "HIGH": {
            "decision": "MAINTENANCE_REQUIRED",
            "next_step": "Generate work order",
            "execution_mode": "planned",
        },
        "MEDIUM": {
            "decision": "INSPECTION_REQUIRED",
            "next_step": "Schedule inspection",
            "execution_mode": "inspection",
        },
        "UNKNOWN": {
            "decision": "ENGINEERING_REVIEW_REQUIRED",
            "next_step": "Escalate to maintenance engineer",
            "execution_mode": "manual_review",
        },
    }

    def decide(self, recommendation):
        priority = recommendation.get("priority", "UNKNOWN")

        decision = self.DECISIONS.get(
            priority,
            self.DECISIONS["UNKNOWN"],
        )

        return {
            "priority": priority,
            "decision": decision["decision"],
            "next_step": decision["next_step"],
            "execution_mode": decision["execution_mode"],
            "reason": recommendation.get("summary", "No reason provided"),
            "actions": recommendation.get("actions", []),
            "recommendation": recommendation.get("recommendation", []),
        }

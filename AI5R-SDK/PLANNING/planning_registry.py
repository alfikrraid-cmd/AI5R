class PlanningRegistry:
    """
    Enterprise Planning Registry

    Stores and retrieves generated plans.
    """

    def __init__(self):
        self.plans = {}

    def register(self, plan):
        if not plan.plan_id:
            raise ValueError("Plan ID is required")

        self.plans[plan.plan_id] = plan

        return {
            "status": "REGISTERED",
            "plan_id": plan.plan_id,
        }

    def get(self, plan_id):
        return self.plans.get(plan_id)

    def list_all(self):
        return list(self.plans.values())

    def list_by_mission(self, mission_id):
        return [
            plan
            for plan in self.list_all()
            if plan.mission_id == mission_id
        ]

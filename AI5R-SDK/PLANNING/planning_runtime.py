from PLANNING.planning_engine import PlanningEngine
from PLANNING.planning_registry import PlanningRegistry


class PlanningRuntime:
    """
    Enterprise Planning Runtime

    Orchestrates plan creation, registration,
    retrieval, and mission-based listing.
    """

    def __init__(self):
        self.engine = PlanningEngine()
        self.registry = PlanningRegistry()

    def create(
        self,
        mission_id,
        goal,
        required_capabilities=None,
        execution_steps=None,
        metadata=None,
    ):
        plan = self.engine.create_plan(
            mission_id=mission_id,
            goal=goal,
            required_capabilities=required_capabilities,
            execution_steps=execution_steps,
            metadata=metadata,
        )

        registration = self.registry.register(plan)

        return {
            "status": "CREATED",
            "registration": registration,
            "plan": plan,
        }

    def get(self, plan_id):
        return self.registry.get(plan_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_mission(self, mission_id):
        return self.registry.list_by_mission(mission_id)

from PLANNING.planning_object import PlanningObject


class PlanningEngine:
    """
    Enterprise Planning Engine

    Converts a mission into an executable plan.
    """

    def create_plan(
        self,
        mission_id,
        goal,
        required_capabilities=None,
        execution_steps=None,
        metadata=None,
    ):
        if not mission_id:
            raise ValueError("Mission ID is required")

        if not goal:
            raise ValueError("Goal is required")

        return PlanningObject(
            mission_id=mission_id,
            goal=goal,
            required_capabilities=required_capabilities or [],
            execution_steps=execution_steps or [],
            metadata=metadata or {},
        )

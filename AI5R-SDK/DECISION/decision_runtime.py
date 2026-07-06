from DECISION.decision_engine import DecisionEngine
from DECISION.decision_registry import DecisionRegistry


class DecisionRuntime:

    def __init__(self):
        self.engine = DecisionEngine()
        self.registry = DecisionRegistry()

    def create(
        self,
        context_id: str,
        objective: str,
        options: list,
        metadata: dict | None = None,
    ):

        decision = self.engine.decide(
            context_id=context_id,
            objective=objective,
            options=options,
            metadata=metadata or {},
        )

        registration = self.registry.register(decision)

        return {
            "status": "CREATED",
            "decision": decision,
            "registration": registration,
        }

    def get(self, decision_id):
        return self.registry.get(decision_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_context(self, context_id):
        return self.registry.list_by_context(context_id)

    def list_by_status(self, status):
        return self.registry.list_by_status(status)

from DECISION.decision_object import DecisionObject


class DecisionRegistry:

    def __init__(self):
        self._objects = {}

    def register(self, decision: DecisionObject):

        self._objects[decision.decision_id] = decision

        return {
            "status": "REGISTERED",
            "decision_id": decision.decision_id,
        }

    def get(self, decision_id: str):
        return self._objects.get(decision_id)

    def list_all(self):
        return list(self._objects.values())

    def list_by_context(self, context_id: str):
        return [
            x
            for x in self._objects.values()
            if x.context_id == context_id
        ]

    def list_by_status(self, status: str):
        return [
            x
            for x in self._objects.values()
            if x.status == status
        ]

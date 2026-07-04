from datetime import datetime, timezone
from uuid import uuid4


try:
    from ENTERPRISE.enterprise_object import EnterpriseObject
except Exception:
    class EnterpriseObject:
        def __init__(self, object_id=None, object_type=None, metadata=None):
            self.id = object_id or str(uuid4())
            self.object_type = object_type or self.__class__.__name__
            self.metadata = metadata or {}


class CognitiveObject(EnterpriseObject):
    def __init__(
        self,
        object_type="cognitive_object",
        version="1.0",
        metadata=None,
        trace_id=None,
        parent_id=None,
        children=None,
        history=None,
        payload=None,
    ):
        generated_id = str(uuid4())

        try:
            super().__init__(
                object_id=generated_id,
                object_type=object_type,
                metadata=metadata or {},
            )
        except TypeError:
            super().__init__()

        self.id = getattr(self, "id", generated_id) or generated_id
        self.object_type = object_type
        self.metadata = metadata or {}

        self.version = version
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.trace_id = trace_id or self.id
        self.parent_id = parent_id
        self.children = children or []
        self.history = history or []
        self.payload = payload or {}

        self.record_history("created")

    def record_history(self, action, data=None):
        self.history.append(
            {
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data or {},
            }
        )

    def add_child(self, child):
        child_id = child.id if hasattr(child, "id") else str(child)
        self.children.append(child_id)
        self.record_history("child_added", {"child_id": child_id})

    def to_dict(self):
        return {
            "id": self.id,
            "object_type": self.object_type,
            "version": self.version,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "children": self.children,
            "history": self.history,
            "payload": self.payload,
        }


class RecommendationObject(CognitiveObject):
    def __init__(self, recommendation=None, **kwargs):
        super().__init__(
            object_type="recommendation_object",
            payload={"recommendation": recommendation or {}},
            **kwargs,
        )


class DecisionObject(CognitiveObject):
    def __init__(self, decision=None, **kwargs):
        super().__init__(
            object_type="decision_object",
            payload={"decision": decision or {}},
            **kwargs,
        )


class PlanObject(CognitiveObject):
    def __init__(self, plan=None, **kwargs):
        super().__init__(
            object_type="plan_object",
            payload={"plan": plan or {}},
            **kwargs,
        )


class ExecutionObject(CognitiveObject):
    def __init__(self, execution=None, **kwargs):
        super().__init__(
            object_type="execution_object",
            payload={"execution": execution or {}},
            **kwargs,
        )


class LearningObject(CognitiveObject):
    def __init__(self, learning=None, **kwargs):
        super().__init__(
            object_type="learning_object",
            payload={"learning": learning or {}},
            **kwargs,
        )

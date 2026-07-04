from PRODUCTS.LTSA_BRAIN.cognitive_objects import (
    CognitiveObject,
    RecommendationObject,
    DecisionObject,
    PlanObject,
    ExecutionObject,
    LearningObject,
)


class EnterpriseCognitivePipeline:
    def __init__(self):
        self.history = []

    def process(self, reality_payload):
        reality = CognitiveObject(
            object_type="reality_object",
            payload={"reality": reality_payload},
            metadata={"stage": "reality"},
        )

        warehouse = self._next_object(
            parent=reality,
            object_type="warehouse_object",
            payload={"warehouse": reality.payload["reality"]},
            stage="warehouse",
        )

        experience = self._next_object(
            parent=warehouse,
            object_type="experience_object",
            payload={"experience": warehouse.payload["warehouse"]},
            stage="experience",
        )

        knowledge = self._next_object(
            parent=experience,
            object_type="knowledge_object",
            payload={"knowledge": experience.payload["experience"]},
            stage="knowledge",
        )

        recommendation = RecommendationObject(
            recommendation={
                "source": knowledge.id,
                "recommendation": "inspect and generate work order",
            },
            trace_id=knowledge.trace_id,
            parent_id=knowledge.id,
            metadata={"stage": "recommendation"},
        )
        knowledge.add_child(recommendation)

        decision = DecisionObject(
            decision={
                "source": recommendation.id,
                "approved": True,
                "reason": "recommendation accepted by default policy",
            },
            trace_id=recommendation.trace_id,
            parent_id=recommendation.id,
            metadata={"stage": "decision"},
        )
        recommendation.add_child(decision)

        plan = PlanObject(
            plan={
                "source": decision.id,
                "steps": [
                    "verify pump finding",
                    "prepare inspection",
                    "generate work order",
                ],
            },
            trace_id=decision.trace_id,
            parent_id=decision.id,
            metadata={"stage": "planning"},
        )
        decision.add_child(plan)

        execution = ExecutionObject(
            execution={
                "source": plan.id,
                "status": "queued",
                "next_action": "dispatch work order",
            },
            trace_id=plan.trace_id,
            parent_id=plan.id,
            metadata={"stage": "execution"},
        )
        plan.add_child(execution)

        learning = LearningObject(
            learning={
                "source": execution.id,
                "status": "pending",
                "lesson": None,
            },
            trace_id=execution.trace_id,
            parent_id=execution.id,
            metadata={"stage": "learning"},
        )
        execution.add_child(learning)

        objects = [
            reality,
            warehouse,
            experience,
            knowledge,
            recommendation,
            decision,
            plan,
            execution,
            learning,
        ]

        self.history = objects

        return {
            "trace_id": reality.trace_id,
            "objects": objects,
            "latest": learning,
        }

    def _next_object(self, parent, object_type, payload, stage):
        obj = CognitiveObject(
            object_type=object_type,
            payload=payload,
            trace_id=parent.trace_id,
            parent_id=parent.id,
            metadata={"stage": stage},
        )

        parent.add_child(obj)

        return obj

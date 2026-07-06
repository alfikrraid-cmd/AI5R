from DECISION.decision_object import DecisionObject


class DecisionEngine:

    def decide(
        self,
        context_id: str,
        objective: str,
        options: list,
        metadata: dict | None = None,
    ) -> DecisionObject:

        if not options:
            raise ValueError("Options are required")

        selected = max(
            options,
            key=lambda x: x.get("score", 0),
        )

        return DecisionObject(
            context_id=context_id,
            objective=objective,
            options=options,
            selected_option=selected,
            rationale="Highest evaluation score",
            confidence_score=selected.get("score", 0),
            metadata=metadata or {},
        )

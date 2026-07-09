from WORKFORCE.sprint import Sprint


class SprintFactory:
    def manufacture(
        self,
        objective: str,
        organization_id: str,
        department_id: str,
        metadata: dict | None = None,
    ):
        if not objective:
            raise ValueError("Sprint objective is required")

        sprint = Sprint(
            objective=objective,
            organization_id=organization_id,
            department_id=department_id,
            metadata=metadata or {},
        )

        return {
            "status": "MANUFACTURED",
            "asset": sprint,
        }

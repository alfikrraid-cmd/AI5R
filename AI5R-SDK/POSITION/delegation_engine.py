class DelegationEngine:

    def delegate(
        self,
        source_position,
        target_position,
        task: dict,
    ):

        if target_position.authority_level > source_position.authority_level:
            return {
                "status": "REJECTED",
                "reason": "Cannot delegate to higher authority position",
            }

        if target_position.status != "ACTIVE":
            return {
                "status": "REJECTED",
                "reason": "Target position is not active",
            }

        return {
            "status": "DELEGATED",
            "source_position_id": source_position.position_id,
            "target_position_id": target_position.position_id,
            "task": task,
        }

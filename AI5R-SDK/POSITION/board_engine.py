class BoardEngine:

    def convene(
        self,
        topic: str,
        positions: list,
        agenda: dict | None = None,
    ):

        if not positions:
            return {
                "status": "REJECTED",
                "reason": "Board requires at least one position",
            }

        members = [
            {
                "position_id": position.position_id,
                "position_code": position.position_code,
                "position_name": position.position_name,
                "authority_level": position.authority_level,
                "department": position.department,
            }
            for position in positions
        ]

        chair = max(
            members,
            key=lambda x: x["authority_level"],
        )

        return {
            "status": "CONVENED",
            "topic": topic,
            "chair": chair,
            "members": members,
            "agenda": agenda or {},
        }

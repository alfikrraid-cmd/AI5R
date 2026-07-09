from HEADQUARTERS.MISSION.mission import Mission


class MissionIntakeEngine:
    def create(
        self,
        title: str,
        description: str = "",
        requester: str = "Human Owner",
        priority: str = "MEDIUM",
        metadata: dict | None = None,
    ) -> Mission:
        if not title.strip():
            raise ValueError("Mission title is required")

        return Mission(
            title=title.strip(),
            description=description.strip(),
            requester=requester,
            priority=priority,
            metadata=metadata or {},
        )

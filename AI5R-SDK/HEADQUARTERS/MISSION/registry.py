from HEADQUARTERS.MISSION.mission import Mission


class MissionRegistry:
    def __init__(self) -> None:
        self._missions: dict[str, Mission] = {}

    def register(self, mission: Mission) -> Mission:
        self._missions[mission.mission_id] = mission
        return mission

    def get(self, mission_id: str) -> Mission:
        if mission_id not in self._missions:
            raise KeyError(f"Mission not found: {mission_id}")
        return self._missions[mission_id]

    def list_all(self) -> list[Mission]:
        return list(self._missions.values())

    def snapshot(self) -> list[dict]:
        return [
            mission.snapshot()
            for mission in self.list_all()
        ]

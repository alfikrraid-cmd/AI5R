from typing import Dict, Any


class EnterpriseBrainRegistry:
    """
    Registry for Enterprise Brain stations.

    Provides lookup and ordered execution metadata.
    """

    def __init__(self):
        self._stations: Dict[str, Any] = {}

    def register(self, stage: str, station: Any):
        if stage in self._stations:
            raise ValueError(f"Stage '{stage}' already registered")

        self._stations[stage] = station

    def get(self, stage: str):
        return self._stations.get(stage)

    def list_stages(self):
        return list(self._stations.keys())

    def count(self):
        return len(self._stations)

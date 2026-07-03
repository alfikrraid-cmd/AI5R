"""
FM-102 Station Registry
"""


class StationRegistry:
    """
    Registry for manufacturing stations.
    """

    def __init__(self):
        self._stations = {}

    def register(self, station):
        self._stations[station.name] = station

    def get(self, name):
        return self._stations.get(name)

    def all(self):
        return list(self._stations.values())

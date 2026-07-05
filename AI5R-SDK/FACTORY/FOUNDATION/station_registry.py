class StationRegistry:
    """
    Registry for manufacturing stations.
    """

    def __init__(self):
        self._stations = {}

    def register(self, name: str, station):
        if name in self._stations:
            raise ValueError(f"Station already registered: {name}")

        self._stations[name] = station
        return station

    def get(self, name: str):
        if name not in self._stations:
            raise ValueError(f"Station not registered: {name}")

        return self._stations[name]

    def all(self):
        return dict(self._stations)

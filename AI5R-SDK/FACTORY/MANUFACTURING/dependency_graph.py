"""
FM-104.3 Manufacturing Dependency Graph
"""


class DependencyGraph:
    """
    Builds a dependency graph from registered manufacturing stations.
    """

    def __init__(self, stations):
        self.stations = stations
        self.graph = {}

    def build(self):
        for station in self.stations:
            self.graph[station.name] = list(station.depends_on)

        return self.graph

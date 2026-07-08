"""
FM-104.6 Manufacturing Engine with Dependency Graph Pipeline
"""

from FACTORY.MANUFACTURING.station_discovery import StationDiscovery
from FACTORY.MANUFACTURING.station_registry import StationRegistry
from FACTORY.MANUFACTURING.dependency_graph import DependencyGraph
from FACTORY.MANUFACTURING.topological_sort import TopologicalSorter


class ManufacturingEngine:

    def __init__(self):

        self.registry = StationRegistry()

        discovery = StationDiscovery()
        stations = discovery.discover("GENERATORS")

        for station in stations:
            self.registry.register(station)

        self.targets = {
            "sql": "database.sql",
            "schema": "schema.json",
            "openapi": "openapi.json",
            "workflow": "workflow.json",
            "release": "release.json"
        }

        graph = DependencyGraph(self.registry.all()).build()
        self.pipeline = TopologicalSorter().sort(graph)

    def manufacture(self, unit, output_dir):

        results = []

        for station_name in self.pipeline:

            station = self.registry.get(station_name)

            if station is None:
                continue

            if station_name not in self.targets:
                continue

            target = f"{output_dir}/{self.targets[station_name]}"

            station.run(unit, target)

            results.append(target)

        return results

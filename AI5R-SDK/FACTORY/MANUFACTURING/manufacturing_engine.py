"""
FM-103.3 Manufacturing Engine with Auto Discovery and Deterministic Order
"""

from MANUFACTURING.station_discovery import StationDiscovery
from MANUFACTURING.station_registry import StationRegistry


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

        self.pipeline = [
            "sql",
            "schema",
            "openapi",
            "workflow",
            "release"
        ]

    def manufacture(self, unit, output_dir):

        results = []

        for station_name in self.pipeline:

            station = self.registry.get(station_name)

            if station is None:
                continue

            target = f"{output_dir}/{self.targets[station_name]}"

            station.run(unit, target)

            results.append(target)

        return results

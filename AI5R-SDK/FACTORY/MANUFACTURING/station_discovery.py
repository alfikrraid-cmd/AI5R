"""
FM-103 Station Discovery
"""

import importlib
import inspect
import pkgutil

from MANUFACTURING.station import ManufacturingStation


class StationDiscovery:

    def discover(self, package_name):

        stations = []

        package = importlib.import_module(package_name)

        for _, module_name, _ in pkgutil.iter_modules(package.__path__):

            module = importlib.import_module(f"{package_name}.{module_name}")

            for _, obj in inspect.getmembers(module, inspect.isclass):

                if obj is ManufacturingStation:
                    continue

                if issubclass(obj, ManufacturingStation):
                    stations.append(obj())

        return stations

"""
FM-104.1 Manufacturing Station Metadata Contract
"""

from abc import ABC, abstractmethod


class ManufacturingStation(ABC):
    """
    Base interface for all manufacturing stations.
    """

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    def depends_on(self):
        return []

    @property
    def version(self):
        return "1.0.0"

    @property
    def stage(self):
        return "manufacturing"

    @abstractmethod
    def run(self, unit, target):
        pass

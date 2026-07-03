"""
FM-101 Manufacturing Station Interface
"""

from abc import ABC, abstractmethod


class ManufacturingStation(ABC):
    """
    Base interface for all manufacturing generators/stations.
    """

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def run(self, unit):
        pass

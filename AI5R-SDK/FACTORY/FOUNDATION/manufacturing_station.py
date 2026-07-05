from abc import ABC, abstractmethod

try:
    from .manufacturing_context import ManufacturingContext
except ImportError:
    from manufacturing_context import ManufacturingContext


class ManufacturingStation(ABC):
    """
    Base interface for every AI5R manufacturing station.
    """

    station_name = "ManufacturingStation"

    @abstractmethod
    def execute(self, context: ManufacturingContext) -> ManufacturingContext:
        pass

    def run(self, context: ManufacturingContext) -> ManufacturingContext:
        context.add_report(
            self.station_name,
            {
                "status": "STARTED",
            },
        )

        result = self.execute(context)

        result.add_report(
            self.station_name,
            {
                "status": "COMPLETED",
            },
        )

        return result

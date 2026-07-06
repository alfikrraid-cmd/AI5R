from MANUFACTURING_STATION import ManufacturingContext
from STATION_REGISTRY import StationRegistry
from WORKFLOW_ENGINE import ManufacturingWorkflow


class StationDispatcher:
    def __init__(self, registry: StationRegistry):
        self.registry = registry

    def dispatch(
        self,
        workflow: ManufacturingWorkflow,
        context: ManufacturingContext,
    ):
        workflow_definition = workflow.validate()

        for station_code in workflow_definition["stations"]:
            station = self.registry.get(station_code)

            if station is None:
                raise ValueError(
                    f"Station '{station_code}' is not registered"
                )

            context = station.execute(context)

        return context

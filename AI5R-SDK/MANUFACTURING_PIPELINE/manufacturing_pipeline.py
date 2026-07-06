from MANUFACTURING_STATION import ManufacturingContext
from STATION_DISPATCHER import StationDispatcher
from STATION_REGISTRY import StationRegistry
from WORKFLOW_ENGINE import ManufacturingWorkflow


class ManufacturingPipeline:
    def __init__(self, registry: StationRegistry):
        self.registry = registry
        self.dispatcher = StationDispatcher(registry)

    def run(
        self,
        product_name: str,
        workflow: ManufacturingWorkflow,
        payload=None,
    ):
        if not product_name:
            raise ValueError("product_name is required")

        context = ManufacturingContext(
            product=product_name.strip().upper().replace(" ", "_").replace("-", "_"),
            payload=payload or {},
        )

        result = self.dispatcher.dispatch(workflow, context)

        return {
            "status": "PIPELINE_COMPLETED",
            "product": result.product,
            "payload": result.payload,
            "history": result.history,
        }

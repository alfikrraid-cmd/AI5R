from MANUFACTURING_PIPELINE import ManufacturingPipeline
from MANUFACTURING_STATION import BaseManufacturingStation
from STATION_REGISTRY import StationRegistry
from WORKFLOW_ENGINE import ManufacturingWorkflow


class KernelSpecificationStation(BaseManufacturingStation):
    station_code = "Specification"
    station_name = "Kernel Specification Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["specification"] = {
            "product": context.product,
            "status": "SPECIFIED",
        }
        return context


class KernelFactoryStation(BaseManufacturingStation):
    station_code = "Factory"
    station_name = "Kernel Factory Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["factory"] = {
            "product": context.product,
            "status": "BUILT",
        }
        return context


class KernelAssemblyStation(BaseManufacturingStation):
    station_code = "Assembly"
    station_name = "Kernel Assembly Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["assembly"] = {
            "product": context.product,
            "status": "ASSEMBLED",
        }
        return context


class KernelArtifactStation(BaseManufacturingStation):
    station_code = "Artifact"
    station_name = "Kernel Artifact Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["artifact"] = {
            "product": context.product,
            "status": "MANUFACTURED",
        }
        return context


class KernelRegistryStation(BaseManufacturingStation):
    station_code = "Registry"
    station_name = "Kernel Registry Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["registry"] = {
            "product": context.product,
            "status": "REGISTERED",
        }
        return context


class KernelRuntimeStation(BaseManufacturingStation):
    station_code = "Runtime"
    station_name = "Kernel Runtime Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["runtime"] = {
            "product": context.product,
            "status": "RUNNING",
        }
        return context


class KernelReleaseStation(BaseManufacturingStation):
    station_code = "Release"
    station_name = "Kernel Release Station"

    def execute(self, context):
        context = super().execute(context)
        context.payload["release"] = {
            "product": context.product,
            "status": "RELEASED",
        }
        return context


class AI5RKernel:
    DEFAULT_STATIONS = [
        "Specification",
        "Factory",
        "Assembly",
        "Artifact",
        "Registry",
        "Runtime",
        "Release",
    ]

    def __init__(self):
        self.registry = StationRegistry()
        self._register_default_stations()
        self.pipeline = ManufacturingPipeline(self.registry)

    def _register_default_stations(self):
        self.registry.register(KernelSpecificationStation())
        self.registry.register(KernelFactoryStation())
        self.registry.register(KernelAssemblyStation())
        self.registry.register(KernelArtifactStation())
        self.registry.register(KernelRegistryStation())
        self.registry.register(KernelRuntimeStation())
        self.registry.register(KernelReleaseStation())

    def manufacture(self, product_name: str, payload=None):
        workflow = ManufacturingWorkflow(
            workflow_name="AI5R_KERNEL_DEFAULT_WORKFLOW",
            stations=self.DEFAULT_STATIONS,
        )

        result = self.pipeline.run(
            product_name=product_name,
            workflow=workflow,
            payload=payload or {},
        )

        return {
            "status": "MANUFACTURED",
            "product": result["product"],
            "payload": result["payload"],
            "history": result["history"],
        }

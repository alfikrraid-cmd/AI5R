try:
    from .build_workspace import BuildWorkspace
    from .build_report import BuildReport
    from .factory_orchestrator import FactoryOrchestrator
    from .manufacturing_event import ManufacturingEvent
    from .manufacturing_event_bus import ManufacturingEventBus
except ImportError:
    from build_workspace import BuildWorkspace
    from build_report import BuildReport
    from factory_orchestrator import FactoryOrchestrator
    from manufacturing_event import ManufacturingEvent
    from manufacturing_event_bus import ManufacturingEventBus


class ManufacturingRuntime:
    """
    Executes full AI5R manufacturing flow.
    """

    def __init__(
        self,
        orchestrator: FactoryOrchestrator,
        event_bus: ManufacturingEventBus | None = None,
    ):
        self.orchestrator = orchestrator
        self.event_bus = event_bus or ManufacturingEventBus()

    def run(self, definition: dict, workspace_root) -> dict:
        workspace = BuildWorkspace(workspace_root)
        workspace_result = workspace.create()

        build_id = definition.get("build_id", "BUILD-UNKNOWN")
        product = definition.get("product", "UNKNOWN")

        self.event_bus.publish(
            ManufacturingEvent(
                event_type="BUILD_STARTED",
                station="ManufacturingRuntime",
                build_id=build_id,
                product=product,
                payload={"workspace": workspace_result},
            )
        )

        manufacturing_result = self.orchestrator.manufacture(definition)

        final_status = manufacturing_result["status"]

        self.event_bus.publish(
            ManufacturingEvent(
                event_type="BUILD_COMPLETED",
                station="ManufacturingRuntime",
                build_id=build_id,
                product=product,
                payload={"status": final_status},
            )
        )

        report = BuildReport(workspace.path("REPORT"))

        report.write_all(
            {
                "build.json": {
                    "build_id": build_id,
                    "product": product,
                    "status": final_status,
                },
                "workspace.json": workspace_result,
                "manufacturing.json": manufacturing_result,
                "events.json": {
                    "events": [
                        event.to_dict()
                        for event in self.event_bus.all()
                    ]
                },
            }
        )

        return {
            "status": "RUNTIME_COMPLETED",
            "workspace": workspace_result,
            "manufacturing": manufacturing_result,
            "events": [
                event.to_dict()
                for event in self.event_bus.all()
            ],
        }

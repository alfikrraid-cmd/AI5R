try:
    from .build_workspace import BuildWorkspace
    from .build_report import BuildReport
    from .factory_orchestrator import FactoryOrchestrator
    from .manufacturing_event import ManufacturingEvent
    from .manufacturing_event_bus import ManufacturingEventBus
    from .manufacturing_context import ManufacturingContext
except ImportError:
    from build_workspace import BuildWorkspace
    from build_report import BuildReport
    from factory_orchestrator import FactoryOrchestrator
    from manufacturing_event import ManufacturingEvent
    from manufacturing_event_bus import ManufacturingEventBus
    from manufacturing_context import ManufacturingContext

from FACTORY.ORDERS.manufacturing_order import ManufacturingOrder
from FACTORY.VALIDATION.manufacturing_order_validator import ManufacturingOrderValidator


class ManufacturingRuntime:
    """
    Executes full AI5R manufacturing flow.

    UMR-001 -- Universal Manufacturing Runtime (MWO-LTSA-049). This class
    remains Chain A from MWO-LTSA-049's own research (WP-000): reused and
    extended, not replaced. It now executes UMC-001's Stage 1 (Manufacturing
    Request, via ManufacturingOrder) and Stage 2 (Manufacturing Context, via
    ManufacturingContext) as its actual entry point, and accepts optional
    identity_resolver/relationship_resolver/factory_pack hooks (UMC-001
    Stages 4-5, and FactoryPack as a first-class Runtime citizen) without
    concrete resolution logic -- a Factory Pack supplies its own
    implementations. Every new parameter defaults to None/absent behavior
    identical to this class's pre-extension form, so every existing caller
    is unaffected.
    """

    def __init__(
        self,
        orchestrator: FactoryOrchestrator,
        event_bus: ManufacturingEventBus | None = None,
        identity_resolver=None,
        relationship_resolver=None,
        factory_pack=None,
    ):
        self.orchestrator = orchestrator
        self.event_bus = event_bus or ManufacturingEventBus()
        self.identity_resolver = identity_resolver
        self.relationship_resolver = relationship_resolver
        self.factory_pack = factory_pack

    def run(self, definition: dict, workspace_root) -> dict:
        workspace = BuildWorkspace(workspace_root)
        workspace_result = workspace.create()

        build_id = definition.get("build_id", "BUILD-UNKNOWN")
        product = definition.get("product", "UNKNOWN")

        # UMC-001 Stage 1 -- Manufacturing Request. Reuses the existing,
        # already-tested ManufacturingOrder/ManufacturingOrderValidator
        # rather than introducing a new request shape.
        order = ManufacturingOrder(
            order_id=build_id,
            requested_product=product,
            customer_request=definition.get(
                "customer_request", f"Manufacture {product} (build {build_id})"
            ),
        )
        order = ManufacturingOrderValidator().validate(order)

        # FactoryPack as a first-class Runtime citizen: validated the same
        # way a ManufacturingOrder is, if one was supplied.
        if self.factory_pack is not None:
            self.factory_pack.validate()

        # UMC-001 Stage 2 -- Manufacturing Context. Threaded through the
        # orchestrator/compiler/pipeline (see factory_orchestrator.py,
        # factory_compiler.py) so any station can read it. Stages 4-5
        # (Identity/Relationship Resolution) are exposed here as available
        # capabilities in context.metadata -- interfaces only, invoked by
        # whichever station manufactures a specific canonical object, not
        # by this generic runtime layer, which has no per-object natural
        # key to resolve against.
        context = ManufacturingContext(
            build_id=build_id,
            product=product,
            version=definition.get("version", ""),
            manifest=definition,
            metadata={
                "identity_resolver": self.identity_resolver,
                "relationship_resolver": self.relationship_resolver,
                "factory_pack": self.factory_pack,
            },
        )

        self.event_bus.publish(
            ManufacturingEvent(
                event_type="BUILD_STARTED",
                station="ManufacturingRuntime",
                build_id=build_id,
                product=product,
                payload={"workspace": workspace_result, "order_status": order.status},
            )
        )

        manufacturing_result = self.orchestrator.manufacture(definition, context=context)

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
            "order_status": order.status,
            "factory_pack": self.factory_pack.pack_code if self.factory_pack is not None else None,
        }

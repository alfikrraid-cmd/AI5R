from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .service_bus import ServiceBus, ServiceEvent
from .service_container import ServiceContainer


@dataclass
class EnterpriseBrainConnector:
    """
    Connects Company Runtime with AI5R OS services.
    """

    container: ServiceContainer
    service_bus: ServiceBus
    metadata: dict[str, Any] = field(default_factory=dict)

    def connect(self, company_runtime):
        self.container.register_instance(
            "company_runtime",
            company_runtime,
        )

        self.service_bus.publish(
            ServiceEvent(
                event_type="COMPANY_CONNECTED",
                payload={
                    "organization": company_runtime.organization.name,
                },
            )
        )

        return {
            "status": "CONNECTED",
            "organization": company_runtime.organization.name,
        }

    def runtime(self):
        return self.container.resolve("company_runtime")

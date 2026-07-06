from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enterprise_brain_connector import EnterpriseBrainConnector
from .kernel_boot_manager import BootTask, KernelBootManager
from .service_bus import ServiceBus
from .service_container import ServiceContainer


@dataclass
class AI5RBootSequence:
    company_runtime: Any
    container: ServiceContainer = field(default_factory=ServiceContainer)
    service_bus: ServiceBus = field(default_factory=ServiceBus)
    boot_manager: KernelBootManager = field(default_factory=KernelBootManager)
    state: str = "CREATED"

    def boot(self):
        connector = EnterpriseBrainConnector(
            container=self.container,
            service_bus=self.service_bus,
        )

        self.boot_manager.register(
            BootTask(
                name="register_service_bus",
                action=lambda: self.container.register_instance(
                    "service_bus",
                    self.service_bus,
                ),
            )
        )

        self.boot_manager.register(
            BootTask(
                name="register_company_runtime",
                action=lambda: connector.connect(self.company_runtime),
            )
        )

        self.boot_manager.register(
            BootTask(
                name="boot_company_runtime",
                action=lambda: self.company_runtime.boot(),
            )
        )

        result = self.boot_manager.boot()

        self.state = "READY"

        return {
            "status": "READY",
            "state": self.state,
            "organization": self.company_runtime.organization.name,
            "executed_tasks": result.executed_tasks,
            "services": self.container.registered_services(),
            "events": [
                event.event_type
                for event in self.service_bus.history()
            ],
        }

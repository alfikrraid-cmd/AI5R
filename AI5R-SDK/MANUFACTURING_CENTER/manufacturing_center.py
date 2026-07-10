from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING.ORDERS import ManufacturingOrder

from .manufacturing_execution_adapter import ManufacturingExecutionAdapter
from .manufacturing_orchestrator import ManufacturingOrchestrator
from .manufacturing_result import ManufacturingResult


@dataclass(slots=True)
class ManufacturingCenter:
    factory: DigitalFactory
    workspace: Path
    adapter: ManufacturingExecutionAdapter = field(
        default_factory=ManufacturingExecutionAdapter
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.workspace, Path):
            raise TypeError("workspace must be a Path")

        if not self.workspace.is_absolute():
            raise ValueError("workspace must be absolute")

        if not self.factory.validate():
            raise ValueError("factory.validate() must return True")

        self.metadata = dict(self.metadata)

    def manufacture(
        self,
        *,
        order: ManufacturingOrder,
    ) -> ManufacturingResult:
        orchestrator = ManufacturingOrchestrator(
            factory=self.factory,
            workspace=self.workspace,
            adapter=self.adapter,
            metadata=self.metadata,
        )

        return orchestrator.manufacture(order=order)

    @property
    def factory_id(self) -> str:
        return self.factory.factory_id

    @property
    def factory_name(self) -> str:
        return self.factory.factory_name

    @property
    def workspace_exists(self) -> bool:
        return self.workspace.exists()

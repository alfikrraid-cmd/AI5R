from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING.ORDERS import ManufacturingOrder

from .manufacturing_context import ManufacturingContext
from .manufacturing_execution_adapter import ManufacturingExecutionAdapter
from .manufacturing_result import ManufacturingResult
from .manufacturing_session import ManufacturingSession
from .manufacturing_status import ManufacturingStatus
from .manufacturing_step import ManufacturingStep


@dataclass(slots=True)
class ManufacturingOrchestrator:
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
        if not order.validate():
            raise ValueError("order.validate() must return True")

        if not order.is_ready_for_planning():
            raise ValueError(
                "order.is_ready_for_planning() must return True"
            )

        session_id = f"SESSION-{order.order_id}"

        merged_metadata: dict[str, Any] = dict(self.metadata)
        merged_metadata.update(dict(order.metadata))

        context = ManufacturingContext(
            manufacturing_id=session_id,
            mwo={
                "order_id": order.order_id,
                "product_type": order.product_type,
                "requirements": dict(order.requirements),
            },
            product_name=order.product_name,
            factory=self.factory.factory_name,
            runtime=self.factory.engine.engine_name,
            workspace=self.workspace,
            metadata=merged_metadata,
        )

        session = ManufacturingSession(
            session_id=session_id,
            order=order,
            context=context,
            metadata=dict(context.metadata),
        )
        session.start()

        step = ManufacturingStep(
            step_id=f"STEP-{order.order_id}",
            capability_id="DIGITAL_FACTORY_MANUFACTURE_ORDER",
            name=f"Manufacture {order.product_name}",
            inputs={
                "order_id": order.order_id,
                "product_type": order.product_type,
            },
            metadata={
                "factory_id": self.factory.factory_id,
                "factory_name": self.factory.factory_name,
            },
        )
        step.start()

        session.transition(
            ManufacturingStatus.MANUFACTURING,
            stage="DigitalFactory",
            progress=50,
        )

        try:
            response = self.factory.manufacture_order(order)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            message = str(exc).strip() or type(exc).__name__

            if not step.is_terminal:
                step.fail(message)

            return session.fail(message)

        return self.adapter.adapt(
            response=response,
            session=session,
            step=step,
        )

    @property
    def factory_id(self) -> str:
        return self.factory.factory_id

    @property
    def factory_name(self) -> str:
        return self.factory.factory_name

    @property
    def workspace_exists(self) -> bool:
        return self.workspace.exists()

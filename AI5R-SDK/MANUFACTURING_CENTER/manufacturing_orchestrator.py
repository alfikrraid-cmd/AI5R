from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING.LINES import ProductionLine
from RUNTIME import RuntimeRequest
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

        recipe = self.factory.get_recipe(order.product_type)
        line = self.factory.get_line(recipe.production_line_id)

        session_id = f"SESSION-{order.order_id}"

        merged_metadata: dict[str, Any] = {
            **self.metadata,
            **dict(order.metadata),
        }

        context = ManufacturingContext(
            manufacturing_id=session_id,
            mwo={
                "order_id": order.order_id,
                "product_type": order.product_type,
                "requirements": dict(order.requirements),
                "recipe_id": recipe.recipe_id,
                "production_line_id": line.line_id,
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

        steps = self._create_steps(
            line=line,
            order=order,
        )

        payload: dict[str, Any] = {
            "order_id": order.order_id,
            "product_name": order.product_name,
            "product_type": order.product_type,
            "recipe_id": recipe.recipe_id,
            "dbom_id": recipe.dbom_id,
            "requirements": dict(order.requirements),
        }

        runtime_metadata: dict[str, Any] = {
            "factory_id": self.factory.factory_id,
            "factory_name": self.factory.factory_name,
            "recipe_version": recipe.version,
            "line_id": line.line_id,
            "line_is_capability_based": line.is_capability_based(),
            **self.factory.metadata,
            **order.metadata,
            **recipe.metadata,
            **line.metadata,
        }

        total_steps = len(steps)

        for index, step in enumerate(steps, start=1):
            progress = max(
                session.progress,
                int(((index - 1) / total_steps) * 90),
            )

            session.transition(
                ManufacturingStatus.MANUFACTURING,
                stage=step.capability_id,
                progress=progress,
            )

            response = self._execute_step(
                step=step,
                payload=payload,
                metadata=runtime_metadata,
            )

            if response.status.value == "FAILED":
                error = response.error or "Runtime capability failed"
                step.fail(error)
                return session.fail(error)

            step.complete(response.output)
            payload = dict(response.output)

        session.transition(
            ManufacturingStatus.TESTING,
            stage="Final Validation",
            progress=90,
        )

        result = session.complete()
        result.metadata["runtime_output"] = dict(payload)
        result.metadata["runtime_profile"] = self.factory.profile
        result.metadata["runtime_definition"] = steps[-1].capability_id
        result.metadata["runtime_metadata"] = dict(runtime_metadata)

        artifacts = payload.get("artifacts", [])
        if isinstance(artifacts, str):
            artifacts = [artifacts]

        if isinstance(artifacts, (list, tuple)):
            for artifact in artifacts:
                if isinstance(artifact, str) and artifact.strip():
                    result.add_artifact(artifact.strip())

        return result

    def _create_steps(
        self,
        *,
        line: ProductionLine,
        order: ManufacturingOrder,
    ) -> list[ManufacturingStep]:
        steps: list[ManufacturingStep] = []

        for index, capability_id in enumerate(
            line.execution_ids(),
            start=1,
        ):
            steps.append(
                ManufacturingStep(
                    step_id=f"STEP-{order.order_id}-{index:03d}",
                    capability_id=capability_id,
                    name=capability_id.replace("_", " ").title(),
                    status=ManufacturingStatus.PENDING,
                    inputs={
                        "order_id": order.order_id,
                        "product_type": order.product_type,
                    },
                    metadata={
                        "factory_id": self.factory.factory_id,
                        "factory_name": self.factory.factory_name,
                        "sequence": index,
                        "total_steps": line.execution_count(),
                    },
                )
            )

        return steps

    def _execute_step(
        self,
        *,
        step: ManufacturingStep,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ):
        step.start()

        return self.factory.engine.execute(
            RuntimeRequest(
                profile=self.factory.profile,
                definition=step.capability_id,
                payload=dict(payload),
                metadata=dict(metadata),
            )
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

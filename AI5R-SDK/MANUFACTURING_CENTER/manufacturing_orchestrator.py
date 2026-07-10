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
from .manufacturing_execution_graph import ManufacturingExecutionGraph
from .manufacturing_parallel_executor import ManufacturingParallelExecutor
from .manufacturing_parallel_plan import ManufacturingParallelPlan
from .manufacturing_payload_merger import ManufacturingPayloadMerger
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

        raw_dependencies = line.metadata.get("dependencies", {})
        if not isinstance(raw_dependencies, dict):
            raise TypeError(
                "line.metadata['dependencies'] must be a dictionary"
            )

        dependencies: dict[str, tuple[str, ...]] = {}

        for capability_id, values in raw_dependencies.items():
            if not isinstance(capability_id, str):
                raise TypeError("dependency capability id must be a string")

            if isinstance(values, str):
                dependencies[capability_id] = (values,)
            elif isinstance(values, (list, tuple)):
                if not all(isinstance(value, str) for value in values):
                    raise TypeError(
                        "dependency entries must be strings"
                    )
                dependencies[capability_id] = tuple(values)
            else:
                raise TypeError(
                    "dependency values must be a string, list, or tuple"
                )

        execution_graph = ManufacturingExecutionGraph.from_line(
            line,
            dependencies=dependencies,
        )
        ordered_capability_ids = execution_graph.execution_order()

        steps = self._create_steps(
            line=line,
            order=order,
            capability_ids=ordered_capability_ids,
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
        completed_steps = 0

        steps_by_capability = {
            step.capability_id: step
            for step in steps
        }

        parallel_plan = ManufacturingParallelPlan(
            graph=execution_graph,
        )
        parallel_executor = ManufacturingParallelExecutor()
        payload_merger = ManufacturingPayloadMerger()
        execution_levels = parallel_plan.execution_levels()

        for level in execution_levels:
            progress = max(
                session.progress,
                int((completed_steps / total_steps) * 90),
            )

            session.transition(
                ManufacturingStatus.MANUFACTURING,
                stage=" + ".join(level),
                progress=progress,
            )

            # Semua capability dalam level menerima snapshot
            # payload yang sama.
            level_payload = dict(payload)

            def run_capability(capability_id: str):
                step = steps_by_capability[capability_id]

                return self._execute_step(
                    step=step,
                    payload=level_payload,
                    metadata=runtime_metadata,
                )

            responses = parallel_executor.execute_level(
                level,
                run_capability,
            )

            level_outputs: dict[str, dict[str, Any]] = {}
            first_error: str | None = None

            # Proses hasil secara deterministik mengikuti urutan level.
            for capability_id in level:
                step = steps_by_capability[capability_id]
                response = responses[capability_id]

                if response.status.value == "FAILED":
                    error = (
                        response.error
                        or "Runtime capability failed"
                    )

                    if not step.is_terminal:
                        step.fail(error)

                    if first_error is None:
                        first_error = error

                    continue

                step.complete(response.output)
                level_outputs[capability_id] = dict(
                    response.output
                )

            if first_error is not None:
                return session.fail(first_error)

            payload = payload_merger.merge(
                base=payload,
                results=level_outputs,
            )

            completed_steps += len(level)

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
        result.metadata["execution_levels"] = [
            list(level) for level in execution_levels
        ]
        result.metadata["max_parallelism"] = (
            parallel_plan.max_parallelism()
        )

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
        capability_ids: tuple[str, ...] | None = None,
    ) -> list[ManufacturingStep]:
        steps: list[ManufacturingStep] = []

        ordered_ids = capability_ids or line.execution_ids()

        for index, capability_id in enumerate(
            ordered_ids,
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
                        "total_steps": len(ordered_ids),
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

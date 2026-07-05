from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class PipelineStep:
    name: str
    runner: Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class PipelineResult:
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)


class PipelineOrchestrator:
    def __init__(self):
        self._steps: list[PipelineStep] = []

    def add_step(self, step: PipelineStep) -> None:
        if not step.name:
            raise ValueError("Pipeline step name is required")

        self._steps.append(step)

    def run(self, initial_payload: dict[str, Any]) -> PipelineResult:
        outputs: dict[str, Any] = {
            "initial_payload": initial_payload,
        }
        current_payload = initial_payload
        executed_steps: list[str] = []

        for step in self._steps:
            current_payload = step.runner(current_payload)
            outputs[step.name] = current_payload
            executed_steps.append(step.name)

        return PipelineResult(
            status="COMPLETED",
            outputs=outputs,
            steps=executed_steps,
        )

    def count(self) -> int:
        return len(self._steps)

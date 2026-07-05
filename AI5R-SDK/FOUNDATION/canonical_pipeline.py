from dataclasses import dataclass, field, asdict
from typing import Any, Callable

from FOUNDATION.canonical_identity import CanonicalIdentityGenerator
from FOUNDATION.canonical_object import utc_now_iso
from FOUNDATION.canonical_event import CanonicalEvent


@dataclass
class PipelineStage:
    stage_id: str
    name: str
    handler: Callable[[Any], Any] | None = None

    def execute(self, payload: Any) -> Any:
        if self.handler is None:
            return payload
        return self.handler(payload)


@dataclass
class CanonicalPipeline:
    pipeline_name: str
    stages: list[PipelineStage] = field(default_factory=list)
    pipeline_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if not self.pipeline_id:
            self.pipeline_id = CanonicalIdentityGenerator.generate("PIPE").value

    def validate(self) -> bool:
        if not self.pipeline_id:
            raise ValueError("pipeline_id is required")
        if not self.pipeline_name:
            raise ValueError("pipeline_name is required")
        return True

    def add_stage(self, stage: PipelineStage) -> "CanonicalPipeline":
        if not stage.stage_id:
            raise ValueError("stage_id is required")
        if not stage.name:
            raise ValueError("stage name is required")

        self.stages.append(stage)
        return self

    def run(self, payload: Any) -> dict[str, Any]:
        self.validate()

        current = payload
        history = []

        for stage in self.stages:
            before = current
            current = stage.execute(current)
            history.append({
                "stage_id": stage.stage_id,
                "stage_name": stage.name,
                "input": before,
                "output": current,
            })

        return {
            "pipeline_id": self.pipeline_id,
            "pipeline_name": self.pipeline_name,
            "input": payload,
            "output": current,
            "history": history,
            "metadata": self.metadata,
        }

    def to_event(self, event_id: str, result: dict[str, Any]) -> CanonicalEvent:
        return CanonicalEvent(
            event_id=event_id,
            event_type="PIPELINE_COMPLETED",
            source_object_id=self.pipeline_id,
            source_object_type="PIPELINE",
            payload=result,
            metadata=self.metadata,
        )

    def serialize(self) -> dict[str, Any]:
        self.validate()

        data = asdict(self)
        data["stages"] = [
            {
                "stage_id": stage.stage_id,
                "name": stage.name,
                "has_handler": stage.handler is not None,
            }
            for stage in self.stages
        ]
        return data

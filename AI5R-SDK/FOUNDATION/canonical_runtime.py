from dataclasses import dataclass, field
from typing import Any

from FOUNDATION.canonical_event import CanonicalEvent
from FOUNDATION.canonical_identity import CanonicalIdentityGenerator
from FOUNDATION.canonical_object import CanonicalObject
from FOUNDATION.canonical_pipeline import CanonicalPipeline
from FOUNDATION.canonical_registry import CanonicalRegistry


@dataclass
class RuntimeResult:
    runtime_id: str
    input_object_id: str
    input_object_type: str
    pipeline_id: str
    output: Any
    events: list[CanonicalEvent] = field(default_factory=list)


class CanonicalRuntime:
    def __init__(self, registry: CanonicalRegistry | None = None):
        self.runtime_id = CanonicalIdentityGenerator.generate("RUN").value
        self.registry = registry or CanonicalRegistry()
        self.events: list[CanonicalEvent] = []

    def register_pipeline(
        self,
        object_type: str,
        pipeline: CanonicalPipeline,
    ) -> None:
        if not object_type:
            raise ValueError("object_type is required")
        if pipeline is None:
            raise ValueError("pipeline is required")

        self.registry.register(
            key=self._pipeline_key(object_type),
            target=pipeline,
            metadata={
                "object_type": object_type,
                "pipeline_id": pipeline.pipeline_id,
            },
        )

    def run(
        self,
        input_object: CanonicalObject,
    ) -> RuntimeResult:
        if input_object is None:
            raise ValueError("input_object is required")

        input_object.validate()

        pipeline = self.registry.resolve(
            self._pipeline_key(input_object.object_type)
        )

        pipeline_result = pipeline.run(input_object.to_dict())

        event = CanonicalEvent(
            event_id=CanonicalIdentityGenerator.generate("EVT").value,
            event_type="RUNTIME_EXECUTED",
            source_object_id=input_object.object_id,
            source_object_type=input_object.object_type,
            payload={
                "runtime_id": self.runtime_id,
                "pipeline_id": pipeline.pipeline_id,
                "pipeline_result": pipeline_result,
            },
        )

        self.events.append(event)

        return RuntimeResult(
            runtime_id=self.runtime_id,
            input_object_id=input_object.object_id,
            input_object_type=input_object.object_type,
            pipeline_id=pipeline.pipeline_id,
            output=pipeline_result["output"],
            events=[event],
        )

    def emitted_events(self) -> list[CanonicalEvent]:
        return self.events

    def _pipeline_key(self, object_type: str) -> str:
        return f"PIPELINE:{object_type.upper()}"

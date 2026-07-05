from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from INTELLIGENCE.REASONING.reasoning_object import ReasoningObject


@dataclass
class ReasoningStationInput:
    reasoning_object: ReasoningObject
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningStationOutput:
    reasoning_object: ReasoningObject
    station_code: str
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ReasoningStationContract(ABC):
    station_code: str = "RS-000"
    station_name: str = "Reasoning Station"

    @abstractmethod
    def process(
        self,
        station_input: ReasoningStationInput,
    ) -> ReasoningStationOutput:
        raise NotImplementedError

    def validate_input(self, station_input: ReasoningStationInput) -> bool:
        if station_input is None:
            raise ValueError("station_input is required")
        if station_input.reasoning_object is None:
            raise ValueError("reasoning_object is required")

        station_input.reasoning_object.validate()
        return True

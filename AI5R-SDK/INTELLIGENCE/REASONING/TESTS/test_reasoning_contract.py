import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.REASONING.CONTRACTS.reasoning_contract import (
    ReasoningStationContract,
    ReasoningStationInput,
    ReasoningStationOutput,
)
from INTELLIGENCE.REASONING.reasoning_object import ReasoningObject


class DummyReasoningStation(ReasoningStationContract):
    station_code = "RS-DUMMY"
    station_name = "Dummy Reasoning Station"

    def process(self, station_input: ReasoningStationInput) -> ReasoningStationOutput:
        self.validate_input(station_input)

        station_input.reasoning_object.add_reasoning_step(
            "dummy station processed"
        )

        return ReasoningStationOutput(
            reasoning_object=station_input.reasoning_object,
            station_code=self.station_code,
            status="processed",
            metadata={"station": self.station_name},
        )


def test_reasoning_station_input_accepts_reasoning_object():
    reasoning = ReasoningObject()

    station_input = ReasoningStationInput(
        reasoning_object=reasoning,
        context={"source": "unit-test"},
    )

    assert station_input.reasoning_object is reasoning
    assert station_input.context["source"] == "unit-test"


def test_reasoning_station_output_contains_contract_fields():
    reasoning = ReasoningObject()

    output = ReasoningStationOutput(
        reasoning_object=reasoning,
        station_code="RS-TEST",
        status="processed",
    )

    assert output.reasoning_object is reasoning
    assert output.station_code == "RS-TEST"
    assert output.status == "processed"


def test_reasoning_station_contract_processes_input():
    station = DummyReasoningStation()
    reasoning = ReasoningObject()

    output = station.process(
        ReasoningStationInput(
            reasoning_object=reasoning,
        )
    )

    assert output.status == "processed"
    assert output.station_code == "RS-DUMMY"
    assert output.reasoning_object.reasoning_path[0] == "dummy station processed"


def test_reasoning_station_contract_rejects_missing_input():
    station = DummyReasoningStation()

    try:
        station.validate_input(None)
        assert False
    except ValueError as error:
        assert "station_input is required" in str(error)

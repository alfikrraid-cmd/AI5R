import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.REASONING.inference_station import InferenceManufacturingStation
from INTELLIGENCE.REASONING.reasoning_object import ReasoningObject
from INTELLIGENCE.REASONING.CONTRACTS.reasoning_contract import ReasoningStationInput


def test_inference_station_manufactures_inference_from_premises():
    station = InferenceManufacturingStation()
    reasoning = ReasoningObject()

    result = station.process(
        ReasoningStationInput(
            reasoning_object=reasoning,
            context={
                "premises": [
                    {
                        "premise_id": "PR-RS004",
                        "knowledge_id": "KO-RS004",
                        "claim": "Factory registry improves integration",
                        "confidence": "HIGH",
                    }
                ],
            },
        )
    )

    assert result.metadata["station_code"] == "RS-004"
    assert result.metadata["inference_count"] == 1
    assert result.inference_objects[0]["inference_id"] == "PR-RS004"
    assert result.inference_objects[0]["conclusion"] == "Factory registry improves integration"
    assert result.inference_objects[0]["confidence"] == "HIGH"
    assert "inference manufactured from premise PR-RS004" in reasoning.reasoning_path
    assert "KO-RS004" in reasoning.supporting_knowledge


def test_inference_station_rejects_missing_premises():
    station = InferenceManufacturingStation()
    reasoning = ReasoningObject()

    try:
        station.process(
            ReasoningStationInput(
                reasoning_object=reasoning,
                context={},
            )
        )
        assert False
    except ValueError as error:
        assert "premises are required" in str(error)

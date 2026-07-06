import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MANUFACTURING_STATION import BaseManufacturingStation
from MANUFACTURING_STATION import ManufacturingContext


class SampleStation(BaseManufacturingStation):
    station_code = "SAMPLE"
    station_name = "Sample Station"


def test_base_manufacturing_station_executes_context():
    context = ManufacturingContext(product="DIGITAL_EMPLOYEE")

    station = SampleStation()
    result = station.execute(context)

    assert result.product == "DIGITAL_EMPLOYEE"
    assert len(result.history) == 1
    assert result.history[0]["station_code"] == "SAMPLE"
    assert result.history[0]["station_name"] == "Sample Station"
    assert result.history[0]["status"] == "COMPLETED"


def test_base_manufacturing_station_requires_context():
    station = SampleStation()

    try:
        station.execute(None)
    except ValueError as error:
        assert str(error) == "context is required"
    else:
        raise AssertionError("Expected ValueError")

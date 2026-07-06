import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MANUFACTURING_STATION import BaseManufacturingStation
from STATION_REGISTRY import StationRegistry


class SampleStation(BaseManufacturingStation):
    station_code = "SAMPLE_STATION"
    station_name = "Sample Station"


def test_station_registry_registers_station():
    registry = StationRegistry()
    station = SampleStation()

    result = registry.register(station)

    assert result["status"] == "REGISTERED"
    assert result["station_code"] == "SAMPLE_STATION"
    assert registry.exists("SAMPLE_STATION") is True


def test_station_registry_gets_station():
    registry = StationRegistry()
    station = SampleStation()

    registry.register(station)

    result = registry.get("SAMPLE_STATION")

    assert result is station


def test_station_registry_lists_stations():
    registry = StationRegistry()
    registry.register(SampleStation())

    result = registry.list()

    assert len(result) == 1
    assert result[0]["station_code"] == "SAMPLE_STATION"


def test_station_registry_unregisters_station():
    registry = StationRegistry()
    registry.register(SampleStation())

    result = registry.unregister("SAMPLE_STATION")

    assert result["status"] == "UNREGISTERED"
    assert registry.exists("SAMPLE_STATION") is False


def test_station_registry_returns_not_found_when_unregistering_unknown():
    registry = StationRegistry()

    result = registry.unregister("UNKNOWN")

    assert result["status"] == "NOT_FOUND"


def test_station_registry_requires_station():
    registry = StationRegistry()

    try:
        registry.register(None)
    except ValueError as error:
        assert str(error) == "station is required"
    else:
        raise AssertionError("Expected ValueError")

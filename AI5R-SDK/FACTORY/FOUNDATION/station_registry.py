class StationRegistry:
    """
    Registry for manufacturing stations.
    """

    def __init__(self):
        self.stations = {}

    def register(self, name: str, station):
        if name in self.stations:
            raise ValueError(f"Station already registered: {name}")

        self.stations[name] = station

        return station

    def get(self, name: str):
        if name not in self.stations:
            raise ValueError(f"Station not registered: {name}")

        return self.stations[name]

    def all(self):
        return dict(self.stations)
EOFcat > AI5R-SDK/FACTORY/FOUNDATION/TESTS/test_station_registry.py <<'EOF'
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.station_registry import StationRegistry


class SampleStation:
    pass


def test_station_registry_registers_station():
    registry = StationRegistry()
    station = SampleStation()

    result = registry.register("sample", station)

    assert result is station
    assert registry.get("sample") is station


def test_station_registry_rejects_duplicate_station():
    registry = StationRegistry()
    station = SampleStation()

    registry.register("sample", station)

    try:
        registry.register("sample", station)
        assert False
    except ValueError as error:
        assert "already registered" in str(error)


def test_station_registry_rejects_unknown_station():
    registry = StationRegistry()

    try:
        registry.get("missing")
        assert False
    except ValueError as error:
        assert "not registered" in str(error)

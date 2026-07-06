import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from STATION_GENERATOR import StationGenerator


def test_station_generator_creates_station(tmp_path):
    generator = StationGenerator(tmp_path)

    result = generator.generate("Factory Station")

    station_path = tmp_path / "FACTORY_STATION"

    assert result["status"] == "STATION_GENERATED"
    assert result["station_code"] == "FACTORY_STATION"
    assert station_path.exists()
    assert (station_path / "__init__.py").exists()
    assert (station_path / "factory_station.py").exists()
    assert (station_path / "station_manifest.py").exists()
    assert (station_path / "TESTS" / "test_factory_station.py").exists()


def test_station_generator_rejects_empty_name(tmp_path):
    generator = StationGenerator(tmp_path)

    try:
        generator.generate("")
    except ValueError as error:
        assert str(error) == "station_name is required"
    else:
        raise AssertionError("Expected ValueError")

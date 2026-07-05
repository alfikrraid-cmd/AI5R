from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.REGISTRY import (
    StationDefinition,
    StationRegistry,
    build_default_station_registry,
)


def test_registry_registers_station():
    registry = StationRegistry()

    station = StationDefinition(
        station_code="MS-TEST",
        station_name="Test Station",
        input_object="InputObject",
        output_object="OutputObject",
        event_type="TEST_EVENT",
        version="1.0",
        owner="AI5R Factory",
    )

    registry.register(station)

    assert registry.count() == 1
    assert registry.get("MS-TEST").station_name == "Test Station"


def test_registry_requires_station_code():
    registry = StationRegistry()

    try:
        registry.register(
            StationDefinition(
                station_code="",
                station_name="Broken Station",
                input_object="InputObject",
                output_object="OutputObject",
                event_type="BROKEN_EVENT",
                version="1.0",
                owner="AI5R Factory",
            )
        )
    except ValueError as exc:
        assert str(exc) == "Station code is required"
    else:
        raise AssertionError("Expected ValueError")


def test_registry_raises_for_unknown_station():
    registry = StationRegistry()

    try:
        registry.get("MS-404")
    except KeyError as exc:
        assert "Station not registered: MS-404" in str(exc)
    else:
        raise AssertionError("Expected KeyError")


def test_default_registry_contains_ltsa_ai_manufacturing_line():
    registry = build_default_station_registry()

    assert registry.count() == 11
    assert registry.get("MS-001").output_object == "RealityObject"
    assert registry.get("MS-011").output_object == "ActionObject"
    assert registry.get("MS-008").event_type == "REASONING_MANUFACTURED"

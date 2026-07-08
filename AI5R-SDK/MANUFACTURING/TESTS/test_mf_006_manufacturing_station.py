from MANUFACTURING import (
    ManufacturingStation,
    StationStatus,
)


def test_station_is_valid():
    station = ManufacturingStation(
        station_id="ST-001",
        station_name="Requirement Station",
        station_type="REQUIREMENT",
        capability_required="REQUIREMENT_ANALYSIS",
    )

    assert station.validate() is True


def test_station_is_available_when_active():
    station = ManufacturingStation(
        station_id="ST-002",
        station_name="QA Station",
        station_type="QA",
        capability_required="QUALITY_ASSURANCE",
    )

    assert station.status == StationStatus.ACTIVE
    assert station.is_available() is True


def test_station_is_not_available_when_maintenance():
    station = ManufacturingStation(
        station_id="ST-003",
        station_name="Deployment Station",
        station_type="DEPLOYMENT",
        capability_required="DEPLOYMENT",
        status=StationStatus.MAINTENANCE,
    )

    assert station.is_available() is False


def test_station_requires_required_fields():
    station = ManufacturingStation(
        station_id="",
        station_name="",
        station_type="",
        capability_required="",
    )

    assert station.validate() is False


def test_station_reuses_manufacturing_object_base():
    station = ManufacturingStation(
        station_id="ST-004",
        station_name="Architecture Station",
        station_type="ARCHITECTURE",
        capability_required="SYSTEM_ARCHITECTURE",
    )

    assert station.canonical_base == "ManufacturingObject"

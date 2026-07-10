from .reality_manufacturing_station import (
RealityManufacturingInput,
RealityManufacturingOutput,
RealityManufacturingStation,
)

all = [
"RealityManufacturingInput",
"RealityManufacturingOutput",
"RealityManufacturingStation",
]
PYcat > AI5R-SDK/FACTORY/STATIONS/TESTS/test_reality_manufacturing_station.py <<'PY'
from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(file).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS import (
RealityManufacturingInput,
RealityManufacturingStation,
)

def test_reality_manufacturing_station_manufactures_reality_object():
station = RealityManufacturingStation()

result = station.manufacture(
    RealityManufacturingInput(
        source="manual_input",
        payload={"observation": "customer needs product recommendation"},
    ),
    context={"product": "LTSA-BRAIN"},
)

assert result.status == "MANUFACTURED"
assert result.station == "MS-001 Reality Manufacturing Station"
assert result.source == "manual_input"
assert result.reality_object["type"] == "REALITY_OBJECT"
assert result.reality_object["payload"]["observation"] == "customer needs product recommendation"
assert result.reality_object["context"]["product"] == "LTSA-BRAIN"
assert result.events[0]["event_type"] == "REALITY_MANUFACTURED"

def test_reality_manufacturing_station_requires_source():
station = RealityManufacturingStation()

try:
    station.manufacture(
        RealityManufacturingInput(
            source="",
            payload={"x": 1},
        )
    )
except ValueError as exc:
    assert str(exc) == "Reality source is required"
else:
    raise AssertionError("Expected ValueError")

def test_reality_manufacturing_station_uses_timezone_aware_datetime():
result = RealityManufacturingStation().manufacture(
RealityManufacturingInput(
source="sensor",
payload={"signal": "ok"},
)
)

parsed = datetime.fromisoformat(result.manufactured_at)

assert parsed.tzinfo is not None


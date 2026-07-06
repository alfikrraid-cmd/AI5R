from pathlib import Path


class StationGenerator:
    def __init__(self, root_path):
        self.root_path = Path(root_path)

    def _normalize(self, station_name: str):
        return station_name.strip().upper().replace(" ", "_").replace("-", "_")

    def _class_name(self, normalized_name: str):
        return "".join(part.title() for part in normalized_name.lower().split("_"))

    def generate(self, station_name: str):
        if not station_name or not station_name.strip():
            raise ValueError("station_name is required")

        normalized = self._normalize(station_name)
        class_name = self._class_name(normalized)

        station_path = self.root_path / normalized
        test_path = station_path / "TESTS"

        station_path.mkdir(parents=True, exist_ok=True)
        test_path.mkdir(parents=True, exist_ok=True)

        (station_path / "__init__.py").write_text(
            f'''from .{normalized.lower()} import {class_name}

__all__ = ["{class_name}"]
''',
            encoding="utf-8",
        )

        (station_path / f"{normalized.lower()}.py").write_text(
            f'''from MANUFACTURING_STATION import BaseManufacturingStation


class {class_name}(BaseManufacturingStation):
    station_code = "{normalized}"
    station_name = "{station_name.strip()}"

    def execute(self, context):
        context = super().execute(context)
        context.payload["{normalized.lower()}"] = "COMPLETED"
        return context
''',
            encoding="utf-8",
        )

        (station_path / "station_manifest.py").write_text(
            f'''STATION_CODE = "{normalized}"
STATION_NAME = "{station_name.strip()}"
STATION_CLASS = "{class_name}"
''',
            encoding="utf-8",
        )

        (test_path / f"test_{normalized.lower()}.py").write_text(
            f'''import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MANUFACTURING_STATION import ManufacturingContext
from {normalized} import {class_name}


def test_{normalized.lower()}_station_executes():
    context = ManufacturingContext(product="DIGITAL_EMPLOYEE")

    station = {class_name}()
    result = station.execute(context)

    assert result.product == "DIGITAL_EMPLOYEE"
    assert result.payload["{normalized.lower()}"] == "COMPLETED"
    assert result.history[0]["station_code"] == "{normalized}"
''',
            encoding="utf-8",
        )

        return {
            "status": "STATION_GENERATED",
            "station_code": normalized,
            "station_name": station_name.strip(),
            "station_path": str(station_path),
        }

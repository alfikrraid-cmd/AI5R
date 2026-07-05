from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext
from FACTORY.FOUNDATION.manufacturing_station import ManufacturingStation


class SampleStation(ManufacturingStation):
    station_name = "SampleStation"

    def execute(self, context):
        context.add_asset("sample_asset.py")
        return context


def test_manufacturing_station_runs_with_context():
    context = ManufacturingContext(
        build_id="BUILD-001",
        product="LTSA-BRAIN",
        version="1.0",
    )

    station = SampleStation()

    result = station.run(context)

    assert result is context
    assert "sample_asset.py" in result.generated_assets
    assert result.reports["SampleStation"]["status"] == "COMPLETED"

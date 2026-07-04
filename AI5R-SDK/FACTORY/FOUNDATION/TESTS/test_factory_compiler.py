from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.manufacturing_pipeline import ManufacturingPipeline
from FACTORY.FOUNDATION.factory_compiler import FactoryCompiler


class CompileStation:
    def run(self, payload):
        payload["compiled_by_station"] = True
        payload["status"] = "STATION_COMPILED"
        return payload


def test_factory_compiler_runs_pipeline():
    pipeline = ManufacturingPipeline()
    pipeline.add_station(CompileStation())

    compiler = FactoryCompiler(pipeline)

    result = compiler.compile({
        "product": "LTSA-BRAIN",
        "version": "1.0",
    })

    assert result["status"] == "FACTORY_COMPILED"
    assert result["product"] == "LTSA-BRAIN"
    assert result["pipeline"]["status"] == "PIPELINE_COMPLETED"
    assert result["pipeline"]["result"]["compiled_by_station"] is True


def test_factory_compiler_requires_product():
    pipeline = ManufacturingPipeline()
    compiler = FactoryCompiler(pipeline)

    try:
        compiler.compile({
            "version": "1.0",
        })
        assert False
    except ValueError as error:
        assert "requires product" in str(error)

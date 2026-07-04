from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.manufacturing_pipeline import ManufacturingPipeline
from FACTORY.FOUNDATION.factory_validator import FactoryValidator
from FACTORY.FOUNDATION.factory_compiler import FactoryCompiler
from FACTORY.FOUNDATION.factory_freeze import FactoryFreeze
from FACTORY.FOUNDATION.factory_orchestrator import FactoryOrchestrator


class BuildStation:
    def run(self, payload):
        payload["built"] = True
        payload["status"] = "BUILT"
        return payload


def test_factory_orchestrator_completes_manufacturing():
    pipeline = ManufacturingPipeline()
    pipeline.add_station(BuildStation())

    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(pipeline),
        freezer=FactoryFreeze(),
    )

    result = orchestrator.manufacture({
        "product": "LTSA-BRAIN",
        "version": "1.0",
        "factory": "AI5R",
    })

    assert result["status"] == "MANUFACTURING_COMPLETED"
    assert result["validation"]["status"] == "VALID"
    assert result["compiled"]["status"] == "FACTORY_COMPILED"
    assert result["frozen"]["status"] == "FROZEN"


def test_factory_orchestrator_rejects_invalid_definition():
    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(ManufacturingPipeline()),
        freezer=FactoryFreeze(),
    )

    result = orchestrator.manufacture({
        "product": "LTSA-BRAIN",
    })

    assert result["status"] == "MANUFACTURING_REJECTED"
    assert result["validation"]["status"] == "INVALID"

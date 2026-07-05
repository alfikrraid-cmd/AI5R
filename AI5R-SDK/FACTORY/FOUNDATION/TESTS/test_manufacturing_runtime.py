from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.manufacturing_pipeline import ManufacturingPipeline
from FACTORY.FOUNDATION.factory_validator import FactoryValidator
from FACTORY.FOUNDATION.factory_compiler import FactoryCompiler
from FACTORY.FOUNDATION.factory_freeze import FactoryFreeze
from FACTORY.FOUNDATION.factory_orchestrator import FactoryOrchestrator
from FACTORY.FOUNDATION.manufacturing_runtime import ManufacturingRuntime


class RuntimeStation:
    def run(self, payload):
        payload["runtime_station"] = True
        payload["status"] = "RUNTIME_STATION_DONE"
        return payload


def test_manufacturing_runtime_completes_build(tmp_path):
    pipeline = ManufacturingPipeline()
    pipeline.add_station(RuntimeStation())

    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(pipeline),
        freezer=FactoryFreeze(),
    )

    runtime = ManufacturingRuntime(orchestrator)

    result = runtime.run(
        definition={
            "build_id": "BUILD-001",
            "product": "LTSA-BRAIN",
            "version": "1.0",
            "factory": "AI5R",
        },
        workspace_root=tmp_path / "BUILD-001",
    )

    assert result["status"] == "RUNTIME_COMPLETED"
    assert result["manufacturing"]["status"] == "MANUFACTURING_COMPLETED"
    assert len(result["events"]) == 2

    assert (tmp_path / "BUILD-001" / "REPORT" / "build.json").exists()
    assert (tmp_path / "BUILD-001" / "REPORT" / "manufacturing.json").exists()
    assert (tmp_path / "BUILD-001" / "REPORT" / "events.json").exists()


def test_manufacturing_runtime_records_rejected_build(tmp_path):
    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(ManufacturingPipeline()),
        freezer=FactoryFreeze(),
    )

    runtime = ManufacturingRuntime(orchestrator)

    result = runtime.run(
        definition={
            "build_id": "BUILD-002",
            "product": "LTSA-BRAIN",
        },
        workspace_root=tmp_path / "BUILD-002",
    )

    assert result["status"] == "RUNTIME_COMPLETED"
    assert result["manufacturing"]["status"] == "MANUFACTURING_REJECTED"
    assert len(result["events"]) == 2
    assert (tmp_path / "BUILD-002" / "REPORT" / "build.json").exists()

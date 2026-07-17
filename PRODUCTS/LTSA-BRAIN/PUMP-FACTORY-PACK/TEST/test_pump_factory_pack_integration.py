"""End-to-end test: a Pump manufactured through the real, unmodified UMR-001
runtime (FACTORY.FOUNDATION.ManufacturingRuntime), using PumpManufacturingStation,
PumpIdentityResolver, and PumpRelationshipResolver as the Factory Pack's own
Stage 3-6 implementation. No FACTORY/PLATFORM file is touched to make this
pass -- every runtime/orchestrator/compiler/pipeline class is reused exactly
as MWO-LTSA-049 (UMR-001) and MWO-LTSA-048 (UMC-001) left it.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/PUMP-FACTORY-PACK/TEST/
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_AI5R_SDK_PATH = Path(__file__).resolve().parents[4] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.FOUNDATION.factory_compiler import FactoryCompiler  # noqa: E402
from FACTORY.FOUNDATION.factory_freeze import FactoryFreeze  # noqa: E402
from FACTORY.FOUNDATION.factory_orchestrator import FactoryOrchestrator  # noqa: E402
from FACTORY.FOUNDATION.factory_validator import FactoryValidator  # noqa: E402
from FACTORY.FOUNDATION.manufacturing_pipeline import ManufacturingPipeline  # noqa: E402
from FACTORY.FOUNDATION.manufacturing_runtime import ManufacturingRuntime  # noqa: E402
from FACTORY.PACKS.factory_pack_loader import FactoryPackLoader  # noqa: E402

from pump_identity_resolver import PumpIdentityResolver  # noqa: E402
from pump_manufacturing_station import PumpManufacturingStation  # noqa: E402
from pump_relationship_resolver import PumpRelationshipResolver  # noqa: E402

PACK_FILE = Path(__file__).resolve().parents[1] / "pump.factory-pack.json"


def _build_runtime(known_pumps=None, seal_registry=None) -> ManufacturingRuntime:
    pipeline = ManufacturingPipeline()
    pipeline.add_station(PumpManufacturingStation())

    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(pipeline),
        freezer=FactoryFreeze(),
    )

    return ManufacturingRuntime(
        orchestrator,
        identity_resolver=PumpIdentityResolver(known_pumps=known_pumps),
        relationship_resolver=PumpRelationshipResolver(seal_registry=seal_registry),
        factory_pack=FactoryPackLoader().load(PACK_FILE),
    )


def test_runtime_manufactures_a_new_pump_end_to_end(tmp_path):
    runtime = _build_runtime(
        known_pumps=[],
        seal_registry=[{"seal_code": "SC-9", "seal_name": "Type 21"}],
    )

    result = runtime.run(
        definition={
            "build_id": "BUILD-PUMP-001",
            "product": "PUMP",
            "version": "1.0",
            "factory": "AI5R",
            "pump": {"tag_number": "P-101", "area": "AREA-1", "seal_type": "Type 21"},
        },
        workspace_root=tmp_path / "BUILD-PUMP-001",
    )

    assert result["status"] == "RUNTIME_COMPLETED"
    assert result["order_status"] == "VALIDATED"
    assert result["factory_pack"] == "FP-PUMP-001"

    pipeline_result = result["manufacturing"]["compiled"]["pipeline"]["result"]
    assert pipeline_result["status"] == "MANUFACTURED"
    assert pipeline_result["manufactured_object"]["payload"]["tag_number"] == "P-101"
    assert (
        pipeline_result["manufactured_object"]["metadata"]["relationship_resolution"]["resolved"]
        == {"seal_type": "SC-9"}
    )

    station_events = result["manufacturing"]["compiled"]["pipeline"]["station_events"]
    assert station_events[0]["station"] == "PumpManufacturingStation"


def test_runtime_rejects_a_pump_that_already_exists(tmp_path):
    runtime = _build_runtime(known_pumps=[{"tag_number": "P-101"}])

    result = runtime.run(
        definition={
            "build_id": "BUILD-PUMP-002",
            "product": "PUMP",
            "version": "1.0",
            "factory": "AI5R",
            "pump": {"tag_number": "P-101", "area": "AREA-1"},
        },
        workspace_root=tmp_path / "BUILD-PUMP-002",
    )

    pipeline_result = result["manufacturing"]["compiled"]["pipeline"]["result"]
    assert pipeline_result["status"] == "PUMP_ALREADY_EXISTS"

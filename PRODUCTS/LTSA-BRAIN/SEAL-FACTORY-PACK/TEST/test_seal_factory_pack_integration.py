"""End-to-end test: a Mechanical Seal manufactured through the real,
unmodified UMR-001 runtime (FACTORY.FOUNDATION.ManufacturingRuntime), using
SealManufacturingStation, SealIdentityResolver, and SealRelationshipResolver
as the Factory Pack's own Stage 3-6 implementation. No FACTORY/PLATFORM file
is touched to make this pass -- every runtime/orchestrator/compiler/pipeline
class is reused exactly as MWO-LTSA-049 (UMR-001) and MWO-LTSA-048 (UMC-001)
left it, and exactly as MWO-LTSA-050 (Pump) already proved. Mirrors
test_pump_factory_pack_integration.py.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/SEAL-FACTORY-PACK/TEST/
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

from seal_identity_resolver import SealIdentityResolver  # noqa: E402
from seal_manufacturing_station import SealManufacturingStation  # noqa: E402
from seal_relationship_resolver import SealRelationshipResolver  # noqa: E402

PACK_FILE = Path(__file__).resolve().parents[1] / "seal.factory-pack.json"


def _build_runtime(known_seals=None, seal_registry=None) -> ManufacturingRuntime:
    pipeline = ManufacturingPipeline()
    pipeline.add_station(SealManufacturingStation())

    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(pipeline),
        freezer=FactoryFreeze(),
    )

    return ManufacturingRuntime(
        orchestrator,
        identity_resolver=SealIdentityResolver(known_seals=known_seals),
        relationship_resolver=SealRelationshipResolver(seal_registry=seal_registry),
        factory_pack=FactoryPackLoader().load(PACK_FILE),
    )


def test_runtime_manufactures_a_new_seal_end_to_end(tmp_path):
    runtime = _build_runtime(
        known_seals=[],
        seal_registry=[{"seal_code": "SC-4", "seal_name": "JC-102"}],
    )

    result = runtime.run(
        definition={
            "build_id": "BUILD-SEAL-001",
            "product": "SEAL",
            "version": "1.0",
            "factory": "AI5R",
            "seal": {
                "seal_code": "SC-9",
                "seal_name": "JC-100",
                "compatible_seal_name": "JC-102",
            },
        },
        workspace_root=tmp_path / "BUILD-SEAL-001",
    )

    assert result["status"] == "RUNTIME_COMPLETED"
    assert result["order_status"] == "VALIDATED"
    assert result["factory_pack"] == "FP-SEAL-001"

    pipeline_result = result["manufacturing"]["compiled"]["pipeline"]["result"]
    assert pipeline_result["status"] == "MANUFACTURED"
    assert pipeline_result["manufactured_object"]["payload"]["seal_code"] == "SC-9"
    assert (
        pipeline_result["manufactured_object"]["metadata"]["relationship_resolution"]["resolved"]
        == {"compatible_seal_name": "SC-4"}
    )

    station_events = result["manufacturing"]["compiled"]["pipeline"]["station_events"]
    assert station_events[0]["station"] == "SealManufacturingStation"


def test_runtime_rejects_a_seal_that_already_exists(tmp_path):
    runtime = _build_runtime(known_seals=[{"seal_code": "SC-9"}])

    result = runtime.run(
        definition={
            "build_id": "BUILD-SEAL-002",
            "product": "SEAL",
            "version": "1.0",
            "factory": "AI5R",
            "seal": {"seal_code": "SC-9", "seal_name": "JC-100"},
        },
        workspace_root=tmp_path / "BUILD-SEAL-002",
    )

    pipeline_result = result["manufacturing"]["compiled"]["pipeline"]["result"]
    assert pipeline_result["status"] == "SEAL_ALREADY_EXISTS"

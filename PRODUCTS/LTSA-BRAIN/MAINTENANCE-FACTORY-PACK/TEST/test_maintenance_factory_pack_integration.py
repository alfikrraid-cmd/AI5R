"""End-to-end test: a Work Order and a Maintenance History record each
manufactured through the real, unmodified UMR-001 runtime
(FACTORY.FOUNDATION.ManufacturingRuntime), using
MaintenanceManufacturingStation, MaintenanceIdentityResolver, and
MaintenanceRelationshipResolver as the Factory Pack's own Stage 3-6
implementation. No FACTORY/PLATFORM file is touched -- every
runtime/orchestrator/compiler/pipeline class is reused exactly as
MWO-LTSA-049 (UMR-001) and MWO-LTSA-048 (UMC-001) left it, and exactly as
MWO-LTSA-050 (Pump) / MWO-LTSA-052 (Seal) already proved. Mirrors
test_pump_factory_pack_integration.py / test_seal_factory_pack_integration.py.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/MAINTENANCE-FACTORY-PACK/TEST/
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

from maintenance_identity_resolver import MaintenanceIdentityResolver  # noqa: E402
from maintenance_manufacturing_station import MaintenanceManufacturingStation  # noqa: E402
from maintenance_relationship_resolver import MaintenanceRelationshipResolver  # noqa: E402

PACK_FILE = Path(__file__).resolve().parents[1] / "maintenance.factory-pack.json"


def _build_runtime(
    known_work_orders=None,
    known_maintenance_records=None,
    known_pumps=None,
) -> ManufacturingRuntime:
    pipeline = ManufacturingPipeline()
    pipeline.add_station(MaintenanceManufacturingStation())

    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(pipeline),
        freezer=FactoryFreeze(),
    )

    return ManufacturingRuntime(
        orchestrator,
        identity_resolver=MaintenanceIdentityResolver(
            known_work_orders=known_work_orders,
            known_maintenance_records=known_maintenance_records,
        ),
        relationship_resolver=MaintenanceRelationshipResolver(
            known_pumps=known_pumps, known_work_orders=known_work_orders
        ),
        factory_pack=FactoryPackLoader().load(PACK_FILE),
    )


def test_runtime_manufactures_a_new_work_order_end_to_end(tmp_path):
    runtime = _build_runtime(known_work_orders=[], known_pumps=[{"tag_number": "P-101"}])

    result = runtime.run(
        definition={
            "build_id": "BUILD-MTN-001",
            "product": "MAINTENANCE",
            "version": "1.0",
            "factory": "AI5R",
            "object_type": "WORK_ORDER",
            "work_order": {
                "work_order_code": "WO-101",
                "description": "Inspect pump seal",
                "asset_code": "P-101",
                "asset_type": "PUMP",
            },
        },
        workspace_root=tmp_path / "BUILD-MTN-001",
    )

    assert result["status"] == "RUNTIME_COMPLETED"
    assert result["order_status"] == "VALIDATED"
    assert result["factory_pack"] == "FP-MAINTENANCE-001"

    pipeline_result = result["manufacturing"]["compiled"]["pipeline"]["result"]
    assert pipeline_result["status"] == "MANUFACTURED"
    assert pipeline_result["manufactured_object"]["payload"]["work_order_code"] == "WO-101"
    assert (
        pipeline_result["manufactured_object"]["metadata"]["relationship_resolution"]["resolved"]
        == {"asset_code": "P-101"}
    )

    station_events = result["manufacturing"]["compiled"]["pipeline"]["station_events"]
    assert station_events[0]["station"] == "MaintenanceManufacturingStation"


def test_runtime_manufactures_a_new_maintenance_record_end_to_end(tmp_path):
    runtime = _build_runtime(
        known_maintenance_records=[],
        known_work_orders=[{"work_order_code": "WO-101"}],
    )

    result = runtime.run(
        definition={
            "build_id": "BUILD-MTN-002",
            "product": "MAINTENANCE",
            "version": "1.0",
            "factory": "AI5R",
            "object_type": "MAINTENANCE_RECORD",
            "maintenance_record": {
                "maintenance_record_code": "MR-001",
                "action_taken": "Replaced seal",
                "work_order_code": "WO-101",
            },
        },
        workspace_root=tmp_path / "BUILD-MTN-002",
    )

    pipeline_result = result["manufacturing"]["compiled"]["pipeline"]["result"]
    assert pipeline_result["status"] == "MANUFACTURED"
    assert pipeline_result["manufactured_object"]["payload"]["maintenance_record_code"] == "MR-001"
    assert (
        pipeline_result["manufactured_object"]["metadata"]["relationship_resolution"]["resolved"]
        == {"work_order_code": "WO-101"}
    )


def test_runtime_rejects_a_work_order_that_already_exists(tmp_path):
    runtime = _build_runtime(known_work_orders=[{"work_order_code": "WO-101"}])

    result = runtime.run(
        definition={
            "build_id": "BUILD-MTN-003",
            "product": "MAINTENANCE",
            "version": "1.0",
            "factory": "AI5R",
            "object_type": "WORK_ORDER",
            "work_order": {"work_order_code": "WO-101", "description": "Inspect"},
        },
        workspace_root=tmp_path / "BUILD-MTN-003",
    )

    pipeline_result = result["manufacturing"]["compiled"]["pipeline"]["result"]
    assert pipeline_result["status"] == "WORK_ORDER_ALREADY_EXISTS"

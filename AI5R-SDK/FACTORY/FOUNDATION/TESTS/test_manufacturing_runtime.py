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
from FACTORY.PACKS.factory_pack import FactoryPack
from FACTORY.RESOLUTION.identity_resolver import IdentityResolution, IdentityResolver
from FACTORY.RESOLUTION.relationship_resolver import (
    RelationshipResolution,
    RelationshipResolver,
)


class RuntimeStation:
    def run(self, payload):
        payload["runtime_station"] = True
        payload["status"] = "RUNTIME_STATION_DONE"
        return payload


class ContextReadingStation:
    """Confirms UMC-001 Stage 2 (Manufacturing Context) actually reaches a
    station, and that Stage 4/5 resolver hooks are reachable via its
    metadata -- without invoking any concrete resolution logic."""

    def run(self, payload):
        context = payload.get("context")

        payload["saw_context"] = context is not None
        payload["saw_identity_resolver"] = (
            context is not None
            and context.metadata.get("identity_resolver") is not None
        )
        payload["status"] = "CONTEXT_READ"
        return payload


class StubIdentityResolver(IdentityResolver):
    def resolve(self, object_type, candidate_key, context):
        return IdentityResolution(matched=False, canonical_id=None, confidence=None)


class StubRelationshipResolver(RelationshipResolver):
    def resolve(self, object_type, candidate_relationships, context):
        return RelationshipResolution()


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


def test_runtime_is_umc001_compliant_for_request_and_context(tmp_path):
    """UMC-001 Stages 1 (Manufacturing Request) and 2 (Manufacturing
    Context): the runtime now builds and validates a ManufacturingOrder,
    and a real ManufacturingContext reaches the station via the pipeline
    payload."""
    pipeline = ManufacturingPipeline()
    pipeline.add_station(ContextReadingStation())

    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(pipeline),
        freezer=FactoryFreeze(),
    )

    runtime = ManufacturingRuntime(
        orchestrator,
        identity_resolver=StubIdentityResolver(),
        relationship_resolver=StubRelationshipResolver(),
    )

    result = runtime.run(
        definition={
            "build_id": "BUILD-003",
            "product": "LTSA-BRAIN",
            "version": "1.0",
            "factory": "AI5R",
        },
        workspace_root=tmp_path / "BUILD-003",
    )

    assert result["order_status"] == "VALIDATED"
    assert result["manufacturing"]["compiled"]["pipeline"]["result"]["saw_context"] is True
    assert (
        result["manufacturing"]["compiled"]["pipeline"]["result"]["saw_identity_resolver"]
        is True
    )


def test_runtime_exposes_station_events_via_pipeline(tmp_path):
    """UMC-001 Stage 7 (Event Publication): per-station events are now
    produced, additively, without changing ManufacturingRuntime's own
    top-level `events` count (still exactly BUILD_STARTED/BUILD_COMPLETED)."""
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
            "build_id": "BUILD-004",
            "product": "LTSA-BRAIN",
            "version": "1.0",
            "factory": "AI5R",
        },
        workspace_root=tmp_path / "BUILD-004",
    )

    station_events = result["manufacturing"]["compiled"]["pipeline"]["station_events"]

    assert len(station_events) == 1
    assert station_events[0]["event_type"] == "STATION_COMPLETED"
    assert station_events[0]["station"] == "RuntimeStation"
    # Top-level runtime events remain exactly BUILD_STARTED/BUILD_COMPLETED --
    # unchanged from every prior test in this file.
    assert len(result["events"]) == 2


def test_runtime_treats_factory_pack_as_first_class_citizen(tmp_path):
    """FactoryPack becomes a Runtime citizen: validated like a
    ManufacturingOrder, and surfaced in the runtime's own result."""
    pipeline = ManufacturingPipeline()
    pipeline.add_station(RuntimeStation())

    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(pipeline),
        freezer=FactoryFreeze(),
    )

    pack = FactoryPack(
        pack_code="LTSA-BRAIN",
        pack_name="LTSA Brain Factory Pack",
        product_type="LTSA-BRAIN",
        capabilities=["ACQUISITION"],
        recipe_path="RECIPES/ltsa-brain.json",
    )

    runtime = ManufacturingRuntime(orchestrator, factory_pack=pack)

    result = runtime.run(
        definition={
            "build_id": "BUILD-005",
            "product": "LTSA-BRAIN",
            "version": "1.0",
            "factory": "AI5R",
        },
        workspace_root=tmp_path / "BUILD-005",
    )

    assert result["factory_pack"] == "LTSA-BRAIN"


def test_runtime_rejects_invalid_factory_pack(tmp_path):
    """An invalid FactoryPack fails the same way an invalid
    ManufacturingOrder would -- fast, before any manufacturing is attempted."""
    pipeline = ManufacturingPipeline()

    orchestrator = FactoryOrchestrator(
        validator=FactoryValidator(),
        compiler=FactoryCompiler(pipeline),
        freezer=FactoryFreeze(),
    )

    invalid_pack = FactoryPack(
        pack_code="",
        pack_name="Broken Pack",
        product_type="LTSA-BRAIN",
        capabilities=["ACQUISITION"],
        recipe_path="RECIPES/broken.json",
    )

    runtime = ManufacturingRuntime(orchestrator, factory_pack=invalid_pack)

    try:
        runtime.run(
            definition={"build_id": "BUILD-006", "product": "LTSA-BRAIN"},
            workspace_root=tmp_path / "BUILD-006",
        )
        assert False, "expected ValueError for an invalid FactoryPack"
    except ValueError:
        pass


def test_default_runtime_behavior_is_unchanged_without_new_hooks(tmp_path):
    """Regression guard: a runtime constructed exactly as every pre-
    MWO-LTSA-049 caller did (no resolver, no factory_pack) still returns the
    same core keys with the same values as before this MWO."""
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
            "build_id": "BUILD-007",
            "product": "LTSA-BRAIN",
            "version": "1.0",
            "factory": "AI5R",
        },
        workspace_root=tmp_path / "BUILD-007",
    )

    assert result["status"] == "RUNTIME_COMPLETED"
    assert result["manufacturing"]["status"] == "MANUFACTURING_COMPLETED"
    assert len(result["events"]) == 2
    assert result["factory_pack"] is None

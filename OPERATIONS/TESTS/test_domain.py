import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from OPERATIONS.SPECIFICATION.specification import OperationsSpecification
from OPERATIONS.FACTORY.factory import OperationsFactory
from OPERATIONS.ARTIFACT.artifact import OperationsArtifact
from OPERATIONS.REGISTRY.registry import OperationsRegistry
from OPERATIONS.RUNTIME.runtime import OperationsRuntime


def test_operations_domain_flow():
    specification = OperationsSpecification().describe()
    built = OperationsFactory().build(specification)
    artifact = OperationsArtifact().create(built)

    registry = OperationsRegistry()
    artifact_id = registry.register("artifact-001", artifact)

    stored_artifact = registry.get(artifact_id)
    runtime_result = OperationsRuntime().run(stored_artifact)

    assert specification["status"] == "READY"
    assert built["status"] == "BUILT"
    assert artifact["status"] == "CREATED"
    assert stored_artifact == artifact
    assert runtime_result["status"] == "RUNNING"

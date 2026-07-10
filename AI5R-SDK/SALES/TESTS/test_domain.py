import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from SALES.SPECIFICATION.specification import SalesSpecification
from SALES.FACTORY.factory import SalesFactory
from SALES.ARTIFACT.artifact import SalesArtifact
from SALES.REGISTRY.registry import SalesRegistry
from SALES.RUNTIME.runtime import SalesRuntime


def test_sales_domain_flow():
    specification = SalesSpecification().describe()
    built = SalesFactory().build(specification)
    artifact = SalesArtifact().create(built)

    registry = SalesRegistry()
    artifact_id = registry.register("artifact-001", artifact)

    stored_artifact = registry.get(artifact_id)
    runtime_result = SalesRuntime().run(stored_artifact)

    assert specification["status"] == "READY"
    assert built["status"] == "BUILT"
    assert artifact["status"] == "CREATED"
    assert stored_artifact == artifact
    assert runtime_result["status"] == "RUNNING"

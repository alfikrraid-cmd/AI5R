import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MARKETING.SPECIFICATION.specification import MarketingSpecification
from MARKETING.FACTORY.factory import MarketingFactory
from MARKETING.ARTIFACT.artifact import MarketingArtifact
from MARKETING.REGISTRY.registry import MarketingRegistry
from MARKETING.RUNTIME.runtime import MarketingRuntime


def test_marketing_domain_flow():
    specification = MarketingSpecification().describe()
    built = MarketingFactory().build(specification)
    artifact = MarketingArtifact().create(built)

    registry = MarketingRegistry()
    artifact_id = registry.register("artifact-001", artifact)

    stored_artifact = registry.get(artifact_id)
    runtime_result = MarketingRuntime().run(stored_artifact)

    assert specification["status"] == "READY"
    assert built["status"] == "BUILT"
    assert artifact["status"] == "CREATED"
    assert stored_artifact == artifact
    assert runtime_result["status"] == "RUNNING"

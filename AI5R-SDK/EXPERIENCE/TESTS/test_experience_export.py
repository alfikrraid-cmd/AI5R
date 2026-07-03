import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXPERIENCE.experience_pipeline import ExperiencePipeline
from EXPERIENCE.experience_export import ExperienceExportContract


def test_experience_export():
    pipeline = ExperiencePipeline()
    exporter = ExperienceExportContract()

    obj = pipeline.process(
        warehouse_object_id="wh001",
        observer_worker_id="worker001",
        observer_type="AI",
        experience_type="technical_observation",
        observation="Mechanical seal failure may be caused by spring fatigue.",
        evidence={
            "source_section": "paragraph 17-24",
            "keywords": ["mechanical seal", "spring fatigue"]
        },
        confidence=0.92,
        organization_id="org001",
        thread_id="thread001",
        metadata={"created_by": "EF-007-test"},
        policy_ids=["POL-001"]
    )

    exported = exporter.export_object(obj)

    assert exported["experience_id"] == obj.id
    assert exported["warehouse_object_id"] == "wh001"
    assert exported["observer"]["worker_id"] == "worker001"
    assert exported["experience_type"] == "technical_observation"
    assert exported["confidence"] == 0.92
    assert exported["context"]["organization_id"] == "org001"

    batch = exporter.export_batch(pipeline.list_all())
    assert len(batch) == 1

    print(exported)
    print("EF-007 Experience Export Contract OK")


if __name__ == "__main__":
    test_experience_export()

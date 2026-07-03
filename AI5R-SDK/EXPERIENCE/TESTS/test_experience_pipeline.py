import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXPERIENCE.experience_pipeline import ExperiencePipeline


def test_experience_pipeline():
    pipeline = ExperiencePipeline()

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
        metadata={"created_by": "EF-006-test"},
        policy_ids=["POL-001"]
    )

    assert obj.is_valid()
    assert obj.warehouse_object_id == "wh001"
    assert len(pipeline.list_all()) == 1
    assert pipeline.list_all()[0].observer_type == "AI"

    print(obj.to_dict())
    print("EF-006 Experience Pipeline OK")


if __name__ == "__main__":
    test_experience_pipeline()

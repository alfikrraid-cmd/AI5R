import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXPERIENCE.experience_object import ExperienceObject


def test_experience_object():
    obj = ExperienceObject(
        id="exp001",
        code="EXP-001",
        warehouse_object_id="wh001",
        observer_worker_id="worker001",
        observer_type="AI",
        experience_type="technical_observation",
        observation="Transcript explains that mechanical seal failure can be caused by spring fatigue.",
        evidence={
            "source_section": "paragraph 17-24",
            "keywords": ["mechanical seal", "spring fatigue"]
        },
        confidence=0.93,
        organization_id="org001",
        metadata={"created_by": "EF-001-test"},
        policy_ids=["POL-001"]
    )

    assert obj.is_valid()

    data = obj.to_dict()

    assert data["id"] == "exp001"
    assert data["warehouse_object_id"] == "wh001"
    assert data["observer_type"] == "AI"
    assert data["confidence"] == 0.93

    print(data)
    print("EF-001 Experience Object OK")


if __name__ == "__main__":
    test_experience_object()

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXPERIENCE.experience_object import ExperienceObject
from EXPERIENCE.experience_registry import ExperienceRegistry


def test_experience_registry():
    registry = ExperienceRegistry()

    obj = ExperienceObject(
        id="exp001",
        code="EXP-001",
        warehouse_object_id="wh001",
        observer_worker_id="worker001",
        observer_type="AI",
        experience_type="technical_observation",
        observation="Mechanical seal failure is related to spring fatigue.",
        evidence={
            "source_section": "paragraph 17-24"
        },
        confidence=0.91,
        organization_id="org001",
        metadata={"created_by": "EF-002-test"},
        policy_ids=["POL-001"]
    )

    registry.register(obj)

    assert registry.get("exp001") == obj
    assert len(registry.list_all()) == 1
    assert len(registry.find_by_warehouse_object("wh001")) == 1
    assert len(registry.find_by_observer("worker001")) == 1
    assert len(registry.find_by_experience_type("technical_observation")) == 1

    print(registry.get("exp001").to_dict())
    print("EF-002 Experience Registry OK")


if __name__ == "__main__":
    test_experience_registry()

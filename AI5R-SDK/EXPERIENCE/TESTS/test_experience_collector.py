import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXPERIENCE.experience_registry import ExperienceRegistry
from EXPERIENCE.experience_collector import ExperienceCollectorEngine


def test_experience_collector():
    registry = ExperienceRegistry()
    collector = ExperienceCollectorEngine(registry)

    obj = collector.collect(
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
        metadata={"created_by": "EF-003-test"},
        policy_ids=["POL-001"]
    )

    assert obj.is_valid()
    assert obj.warehouse_object_id == "wh001"
    assert obj.observer_worker_id == "worker001"
    assert registry.get(obj.id) == obj
    assert len(registry.list_all()) == 1

    print(obj.to_dict())
    print("EF-003 Experience Collector Engine OK")


if __name__ == "__main__":
    test_experience_collector()

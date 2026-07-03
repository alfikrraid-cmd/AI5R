import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXPERIENCE.experience_registry import ExperienceRegistry
from EXPERIENCE.experience_collector import ExperienceCollectorEngine
from EXPERIENCE.experience_query import ExperienceQueryEngine


def test_experience_query():
    registry = ExperienceRegistry()
    collector = ExperienceCollectorEngine(registry)
    query = ExperienceQueryEngine(registry)

    collector.collect(
        warehouse_object_id="wh001",
        observer_worker_id="worker001",
        observer_type="AI",
        experience_type="technical_observation",
        observation="Mechanical seal failure may be caused by spring fatigue.",
        evidence={"source_section": "paragraph 17-24"},
        confidence=0.92,
        metadata={"created_by": "EF-005-test"},
        policy_ids=["POL-001"]
    )

    collector.collect(
        warehouse_object_id="wh002",
        observer_worker_id="worker002",
        observer_type="human",
        experience_type="field_observation",
        observation="Pump vibration increased after bearing replacement.",
        evidence={"field_report": "FR-001"},
        confidence=0.81,
        metadata={"created_by": "EF-005-test"},
        policy_ids=["POL-002"]
    )

    assert len(query.all()) == 2
    assert len(query.by_warehouse_object("wh001")) == 1
    assert len(query.by_observer("worker001")) == 1
    assert len(query.by_experience_type("field_observation")) == 1
    assert len(query.by_policy("POL-001")) == 1
    assert len(query.by_metadata("created_by", "EF-005-test")) == 2
    assert len(query.by_min_confidence(0.9)) == 1

    print([obj.to_dict() for obj in query.all()])
    print("EF-005 Experience Query Engine OK")


if __name__ == "__main__":
    test_experience_query()

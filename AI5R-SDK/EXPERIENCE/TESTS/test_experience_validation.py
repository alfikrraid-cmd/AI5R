import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXPERIENCE.experience_object import ExperienceObject
from EXPERIENCE.experience_validation import ExperienceValidationEngine


def test_experience_validation():
    validator = ExperienceValidationEngine()

    valid_obj = ExperienceObject(
        id="exp001",
        code="EXP-001",
        warehouse_object_id="wh001",
        observer_worker_id="worker001",
        observer_type="AI",
        experience_type="technical_observation",
        observation="Mechanical seal failure may be caused by spring fatigue.",
        evidence={"source_section": "paragraph 17-24"},
        confidence=0.92
    )

    invalid_obj = ExperienceObject(
        id="",
        code="",
        warehouse_object_id="",
        observer_worker_id="",
        observer_type="",
        experience_type="",
        observation="",
        evidence={},
        confidence=1.5
    )

    assert validator.validate(valid_obj)
    assert not validator.validate(invalid_obj)
    assert len(validator.errors(valid_obj)) == 0
    assert len(validator.errors(invalid_obj)) > 0
    assert not validator.validate_batch([valid_obj, invalid_obj])

    print(validator.errors(invalid_obj))
    print("EF-004 Experience Validation Engine OK")


if __name__ == "__main__":
    test_experience_validation()

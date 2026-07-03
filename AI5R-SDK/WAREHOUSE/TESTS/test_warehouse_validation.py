import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WAREHOUSE.warehouse_object import WarehouseObject
from WAREHOUSE.warehouse_validation import WarehouseValidationEngine


def test_warehouse_validation():
    validator = WarehouseValidationEngine()

    valid_obj = WarehouseObject(
        id="wh001",
        code="WH-001",
        source_type="youtube",
        source_id="yt001",
        object_type="raw_transcript",
        payload={
            "title": "Pump Basics",
            "content": "Pump explanation..."
        }
    )

    invalid_obj = WarehouseObject(
        id="",
        code="",
        source_type="",
        source_id="",
        object_type="",
        payload={}
    )

    assert validator.validate(valid_obj)
    assert not validator.validate(invalid_obj)
    assert len(validator.errors(valid_obj)) == 0
    assert len(validator.errors(invalid_obj)) > 0
    assert not validator.validate_batch([valid_obj, invalid_obj])

    print(validator.errors(invalid_obj))
    print("WF-005 Warehouse Validation Engine OK")


if __name__ == "__main__":
    test_warehouse_validation()

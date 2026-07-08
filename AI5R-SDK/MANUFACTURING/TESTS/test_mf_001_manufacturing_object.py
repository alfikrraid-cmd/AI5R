from MANUFACTURING import (
    ManufacturingObject,
    ManufacturingObjectType,
)


def test_manufacturing_object_is_valid():
    obj = ManufacturingObject(
        object_id="MF-OBJ-001",
        object_type=ManufacturingObjectType.FACTORY,
        name="Software Factory",
    )

    assert obj.validate() is True


def test_manufacturing_object_reuses_enterprise_object():
    obj = ManufacturingObject(
        object_id="MF-OBJ-002",
        object_type=ManufacturingObjectType.RECIPE,
        name="Website Recipe",
    )

    assert obj.canonical_base == "EnterpriseObject"
    assert obj.is_canonical_reuse() is True


def test_manufacturing_object_rejects_missing_id():
    obj = ManufacturingObject(
        object_id="",
        object_type=ManufacturingObjectType.PRODUCT,
        name="AI Agent",
    )

    assert obj.validate() is False


def test_manufacturing_object_contains_required_types():
    required = {
        "FACTORY",
        "RECIPE",
        "DBOM",
        "MANUFACTURING_ORDER",
        "PRODUCTION_SCHEDULER",
        "MANUFACTURING_LINE",
        "MANUFACTURING_STATION",
        "QUALITY_ASSURANCE",
        "PACKAGE",
        "DEPLOYMENT",
        "PRODUCT",
    }

    actual = {item.value for item in ManufacturingObjectType}

    assert required.issubset(actual)

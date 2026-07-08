import pytest

from FACTORY.ORDERS.manufacturing_order import ManufacturingOrder
from FACTORY.VALIDATION.manufacturing_order_validator import (
    ManufacturingOrderValidator,
)


def test_validator_changes_status_to_validated():
    order = ManufacturingOrder(
        order_id="ORDER-001",
        requested_product="WEBSITE",
        customer_request="Build company website",
    )

    validator = ManufacturingOrderValidator()

    validated = validator.validate(order)

    assert validated.status == "VALIDATED"


def test_validator_rejects_invalid_order():
    order = ManufacturingOrder(
        order_id="",
        requested_product="",
        customer_request="",
    )

    validator = ManufacturingOrderValidator()

    with pytest.raises(ValueError):
        validator.validate(order)

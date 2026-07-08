import pytest

from FACTORY.ORDERS.manufacturing_order import ManufacturingOrder


def test_manufacturing_order_validates():
    order = ManufacturingOrder(
        order_id="ORDER-001",
        requested_product="WEBSITE",
        customer_request="I want a company website",
    )

    assert order.validate() is True
    assert order.status == "CREATED"


def test_manufacturing_order_requires_product():
    order = ManufacturingOrder(
        order_id="ORDER-001",
        requested_product="",
        customer_request="I want a company website",
    )

    with pytest.raises(ValueError):
        order.validate()

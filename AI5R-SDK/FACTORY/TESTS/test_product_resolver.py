import pytest

from FACTORY.ORDERS.manufacturing_order import ManufacturingOrder
from FACTORY.RESOLUTION.product_resolver import ProductResolver


def test_resolve_website():
    order = ManufacturingOrder(
        order_id="ORDER-001",
        requested_product="WEBSITE",
        customer_request="Build Website",
        status="VALIDATED",
    )

    resolver = ProductResolver()

    assert resolver.resolve(order) == "WEBSITE_PRODUCT_PACK"


def test_order_must_be_validated():
    order = ManufacturingOrder(
        order_id="ORDER-001",
        requested_product="WEBSITE",
        customer_request="Build Website",
    )

    resolver = ProductResolver()

    with pytest.raises(ValueError):
        resolver.resolve(order)


def test_unknown_product():
    order = ManufacturingOrder(
        order_id="ORDER-001",
        requested_product="UNKNOWN",
        customer_request="Build Something",
        status="VALIDATED",
    )

    resolver = ProductResolver()

    with pytest.raises(ValueError):
        resolver.resolve(order)

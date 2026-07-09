from ARCHITECTURE.canonical_factory_map import (
    CANONICAL_FACTORY_MAP,
    get_canonical,
    get_status,
    list_components_needing_confirmation,
)


def test_manufacturing_order_canonical_is_manufacturing_package():
    assert get_canonical("manufacturing_order") == "MANUFACTURING.ORDERS.manufacturing_order"


def test_manufacturing_order_status_is_confirmed():
    assert get_status("manufacturing_order") == "CANONICAL_CONFIRMED"


def test_factory_order_is_compatibility_only():
    compatibility = CANONICAL_FACTORY_MAP["manufacturing_order"]["compatibility"]

    assert "FACTORY.ORDERS.manufacturing_order" in compatibility


def test_confirmed_manufacturing_order_not_pending_review():
    pending = list_components_needing_confirmation()

    assert "manufacturing_order" not in pending


def test_canonical_first_rule_is_recorded():
    rule = CANONICAL_FACTORY_MAP["manufacturing_order"]["rule"]

    assert "All new code" in rule
    assert "MANUFACTURING.ORDERS.ManufacturingOrder" in rule

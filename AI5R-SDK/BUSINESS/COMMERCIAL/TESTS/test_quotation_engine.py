from BUSINESS.COMMERCIAL.QUOTATION import QuotationEngine, QuotationItem


def test_create_quotation():
    engine = QuotationEngine()

    quotation = engine.create(
        quotation_id="Q-001",
        customer_id="CUST-001",
    )

    assert quotation.quotation_id == "Q-001"
    assert quotation.customer_id == "CUST-001"
    assert quotation.currency == "IDR"


def test_add_item():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001")

    engine.add_item(
        quotation,
        QuotationItem(
            description="AI5R Sales Workforce Setup",
            quantity=1,
            unit_price=50_000_000,
        ),
    )

    assert len(quotation.items) == 1
    assert quotation.subtotal == 50_000_000


def test_multiple_items():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001")

    engine.add_item(quotation, QuotationItem("Setup", 1, 50_000_000))
    engine.add_item(quotation, QuotationItem("Training", 2, 5_000_000))

    assert quotation.subtotal == 60_000_000


def test_discount():
    item = QuotationItem(
        description="Setup",
        quantity=1,
        unit_price=50_000_000,
        discount=5_000_000,
    )

    assert item.subtotal == 50_000_000
    assert item.total == 45_000_000


def test_tax():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001", tax_rate=0.11)

    engine.add_item(quotation, QuotationItem("Setup", 1, 100_000_000))

    assert quotation.tax == 11_000_000


def test_grand_total():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001", tax_rate=0.11)

    engine.add_item(quotation, QuotationItem("Setup", 1, 100_000_000))

    assert quotation.grand_total == 111_000_000


def test_remove_item():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001")

    engine.add_item(quotation, QuotationItem("Setup", 1, 50_000_000))
    engine.remove_item(quotation, 0)

    assert quotation.items == []
    assert quotation.subtotal == 0


def test_empty_quotation():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001")

    assert quotation.subtotal == 0
    assert quotation.tax == 0
    assert quotation.grand_total == 0


def test_zero_tax():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001", tax_rate=0)

    engine.add_item(quotation, QuotationItem("Setup", 1, 100_000_000))

    assert quotation.tax == 0
    assert quotation.grand_total == 100_000_000


def test_decimal_quantity():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001", tax_rate=0)

    engine.add_item(quotation, QuotationItem("Consulting Hour", 1.5, 1_000_000))

    assert quotation.subtotal == 1_500_000


def test_reject_negative_tax():
    engine = QuotationEngine()

    try:
        engine.create("Q-001", "CUST-001", tax_rate=-0.1)
    except ValueError as exc:
        assert "Tax rate" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_reject_negative_quantity():
    engine = QuotationEngine()
    quotation = engine.create("Q-001", "CUST-001")

    try:
        engine.add_item(quotation, QuotationItem("Setup", -1, 50_000_000))
    except ValueError as exc:
        assert "Quantity" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

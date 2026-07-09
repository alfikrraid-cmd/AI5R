from SALES.CRM import Customer, CustomerInteraction, SalesCRMRuntime


def test_add_customer():
    crm = SalesCRMRuntime()

    customer = Customer(
        customer_id="CUST-001",
        name="PT Astra",
        segment="ENTERPRISE",
    )

    crm.add_customer(customer)

    assert crm.get_customer("CUST-001").name == "PT Astra"


def test_reject_duplicate_customer():
    crm = SalesCRMRuntime()

    customer = Customer(customer_id="CUST-001", name="PT Astra")

    crm.add_customer(customer)

    try:
        crm.add_customer(customer)
    except ValueError as exc:
        assert "Duplicate customer" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_record_customer_interaction():
    crm = SalesCRMRuntime()

    crm.add_customer(Customer(customer_id="CUST-001", name="PT Astra"))

    crm.record_interaction(
        CustomerInteraction(
            interaction_id="INT-001",
            customer_id="CUST-001",
            interaction_type="MEETING",
            notes="Customer interested but concerned about price.",
        )
    )

    history = crm.customer_history("CUST-001")

    assert len(history) == 1
    assert "concerned about price" in history[0].notes


def test_latest_interaction():
    crm = SalesCRMRuntime()

    crm.add_customer(Customer(customer_id="CUST-001", name="PT Astra"))

    crm.record_interaction(
        CustomerInteraction(
            interaction_id="INT-001",
            customer_id="CUST-001",
            interaction_type="CALL",
            notes="Initial contact.",
        )
    )

    crm.record_interaction(
        CustomerInteraction(
            interaction_id="INT-002",
            customer_id="CUST-001",
            interaction_type="MEETING",
            notes="Discussed proposal.",
        )
    )

    latest = crm.latest_interaction("CUST-001")

    assert latest is not None
    assert latest.interaction_id == "INT-002"


def test_next_followup():
    crm = SalesCRMRuntime()

    crm.add_customer(Customer(customer_id="CUST-001", name="PT Astra"))

    crm.record_interaction(
        CustomerInteraction(
            interaction_id="INT-001",
            customer_id="CUST-001",
            interaction_type="MEETING",
            notes="Follow up required.",
            next_followup_at="2026-07-12",
        )
    )

    assert crm.next_followup("CUST-001") == "2026-07-12"


def test_update_customer_status():
    crm = SalesCRMRuntime()

    crm.add_customer(Customer(customer_id="CUST-001", name="PT Astra"))

    customer = crm.update_status("CUST-001", "NEGOTIATION")

    assert customer.status == "NEGOTIATION"

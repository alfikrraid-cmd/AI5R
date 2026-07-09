from BUSINESS.COMMERCIAL.CONTRACT import (
    ContractEngine,
    ContractParty,
    ContractStatus,
)


def test_create_contract():
    engine = ContractEngine()

    contract = engine.create(
        contract_id="CON-001",
        customer_id="CUST-001",
        title="AI5R Implementation Contract",
        value=100_000_000,
    )

    assert contract.contract_id == "CON-001"
    assert contract.customer_id == "CUST-001"
    assert contract.status == ContractStatus.DRAFT


def test_add_party():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")

    engine.add_party(
        contract,
        ContractParty("P-001", "PT Client", "CLIENT"),
    )

    assert len(contract.parties) == 1


def test_reject_duplicate_party():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")
    party = ContractParty("P-001", "PT Client", "CLIENT")

    engine.add_party(contract, party)

    try:
        engine.add_party(contract, party)
    except ValueError as exc:
        assert "Duplicate party" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_submit_for_review():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")

    engine.submit_for_review(contract)

    assert contract.status == ContractStatus.REVIEW


def test_approve_contract():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")

    engine.submit_for_review(contract)
    engine.approve(contract)

    assert contract.status == ContractStatus.APPROVED


def test_activate_contract():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")

    engine.submit_for_review(contract)
    engine.approve(contract)
    engine.activate(contract)

    assert contract.status == ContractStatus.ACTIVE
    assert contract.is_active is True


def test_complete_contract():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")

    engine.submit_for_review(contract)
    engine.approve(contract)
    engine.activate(contract)
    engine.complete(contract)

    assert contract.status == ContractStatus.COMPLETED
    assert contract.is_active is False


def test_cancel_contract():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")

    engine.cancel(contract)

    assert contract.status == ContractStatus.CANCELLED


def test_invalid_transition():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")

    try:
        engine.activate(contract)
    except ValueError as exc:
        assert "Invalid transition" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_reject_missing_customer():
    engine = ContractEngine()

    try:
        engine.create("CON-001", "", "Contract")
    except ValueError as exc:
        assert "Customer ID" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_terminate_active_contract():
    engine = ContractEngine()
    contract = engine.create("CON-001", "CUST-001", "Contract")

    engine.submit_for_review(contract)
    engine.approve(contract)
    engine.activate(contract)
    engine.terminate(contract)

    assert contract.status == ContractStatus.TERMINATED
    assert contract.is_active is False

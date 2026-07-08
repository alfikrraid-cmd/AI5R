from ENTERPRISE.OPERATING_STACK import (
    EnterpriseOperatingLayer,
    EnterpriseOperatingStack,
)


def test_enterprise_operating_stack_order_is_valid():
    stack = EnterpriseOperatingStack()

    assert stack.validate() is True


def test_enterprise_operating_stack_contains_required_layers():
    stack = EnterpriseOperatingStack()

    assert EnterpriseOperatingLayer.OBJECT.value in stack.layer_names()
    assert EnterpriseOperatingLayer.EVENT.value in stack.layer_names()
    assert EnterpriseOperatingLayer.DOCUMENT.value in stack.layer_names()
    assert EnterpriseOperatingLayer.WORKFLOW.value in stack.layer_names()
    assert EnterpriseOperatingLayer.TRANSACTION.value in stack.layer_names()
    assert EnterpriseOperatingLayer.ACCOUNTING.value in stack.layer_names()
    assert EnterpriseOperatingLayer.EXECUTIVE_INTELLIGENCE.value in stack.layer_names()


def test_vertical_modules_cannot_create_journal_directly():
    stack = EnterpriseOperatingStack()

    assert stack.allows_direct_journal_from_vertical() is False


def test_accounting_entries_must_come_from_transaction_layer():
    stack = EnterpriseOperatingStack()

    assert stack.accounting_entry_source() == "ENTERPRISE_TRANSACTION"


def test_stack_principles_lock_document_workflow_transaction_accounting_flow():
    stack = EnterpriseOperatingStack()

    assert "Every business process starts from EnterpriseDocument" in stack.principles
    assert "Every EnterpriseDocument must pass through EnterpriseWorkflow" in stack.principles
    assert "Only completed workflows may produce EnterpriseTransaction" in stack.principles
    assert "Only EnterpriseAccounting may translate transactions into journal entries" in stack.principles

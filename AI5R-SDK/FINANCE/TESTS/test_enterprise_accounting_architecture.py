from FINANCE.ACCOUNTING import (
    AccountType,
    AccountingObjectType,
    AccountingRelationshipType,
    EnterpriseAccountingArchitecture,
    NormalBalance,
)


def test_eaa_uses_enterprise_kernel():
    architecture = EnterpriseAccountingArchitecture()

    assert architecture.kernel == "EnterpriseKernel"
    assert architecture.graph == "EnterpriseKnowledgeGraph"
    assert architecture.object_base == "EnterpriseObject"


def test_eaa_uses_standard_double_entry_accounting():
    architecture = EnterpriseAccountingArchitecture()

    assert architecture.standard == "Double-entry accounting"


def test_eaa_is_valid():
    architecture = EnterpriseAccountingArchitecture()

    assert architecture.validate() is True


def test_standard_account_types_exist():
    architecture = EnterpriseAccountingArchitecture()

    assert architecture.normal_balance_for(AccountType.ASSET) == NormalBalance.DEBIT
    assert architecture.normal_balance_for(AccountType.EXPENSE) == NormalBalance.DEBIT
    assert architecture.normal_balance_for(AccountType.LIABILITY) == NormalBalance.CREDIT
    assert architecture.normal_balance_for(AccountType.EQUITY) == NormalBalance.CREDIT
    assert architecture.normal_balance_for(AccountType.REVENUE) == NormalBalance.CREDIT


def test_all_accounting_objects_use_enterprise_object():
    architecture = EnterpriseAccountingArchitecture()

    for rule in architecture.object_rules:
        assert rule.base_object == "EnterpriseObject"
        assert rule.relationship_engine == "EnterpriseKnowledgeGraph"
        assert rule.reusable_across_verticals is True


def test_eaa_contains_required_accounting_objects():
    architecture = EnterpriseAccountingArchitecture()

    assert AccountingObjectType.COMPANY.value in architecture.object_type_names()
    assert AccountingObjectType.PROJECT.value in architecture.object_type_names()
    assert AccountingObjectType.ACCOUNT.value in architecture.object_type_names()
    assert AccountingObjectType.CHART_OF_ACCOUNTS.value in architecture.object_type_names()
    assert AccountingObjectType.JOURNAL_ENTRY.value in architecture.object_type_names()
    assert AccountingObjectType.JOURNAL_LINE.value in architecture.object_type_names()
    assert AccountingObjectType.GENERAL_LEDGER.value in architecture.object_type_names()
    assert AccountingObjectType.LEDGER_ENTRY.value in architecture.object_type_names()
    assert AccountingObjectType.INVOICE.value in architecture.object_type_names()
    assert AccountingObjectType.PAYMENT.value in architecture.object_type_names()


def test_eaa_contains_required_relationships():
    architecture = EnterpriseAccountingArchitecture()

    assert AccountingRelationshipType.OWNS.value in architecture.relationship_type_names()
    assert AccountingRelationshipType.BELONGS_TO.value in architecture.relationship_type_names()
    assert AccountingRelationshipType.BILLS.value in architecture.relationship_type_names()
    assert AccountingRelationshipType.PAYS.value in architecture.relationship_type_names()
    assert AccountingRelationshipType.RECORDS.value in architecture.relationship_type_names()
    assert AccountingRelationshipType.POSTS_TO.value in architecture.relationship_type_names()
    assert AccountingRelationshipType.ALLOCATES_TO.value in architecture.relationship_type_names()


def test_eaa_default_currency_is_idr():
    architecture = EnterpriseAccountingArchitecture()

    assert architecture.currency_default == "IDR"

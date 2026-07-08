from dataclasses import dataclass, field
from enum import Enum


class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class NormalBalance(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class AccountingObjectType(str, Enum):
    COMPANY = "COMPANY"
    PROJECT = "PROJECT"
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    ACCOUNT = "ACCOUNT"
    CHART_OF_ACCOUNTS = "CHART_OF_ACCOUNTS"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    JOURNAL_LINE = "JOURNAL_LINE"
    GENERAL_LEDGER = "GENERAL_LEDGER"
    LEDGER_ENTRY = "LEDGER_ENTRY"
    INVOICE = "INVOICE"
    PAYMENT = "PAYMENT"
    EXPENSE = "EXPENSE"
    TAX = "TAX"
    BUDGET = "BUDGET"


class AccountingRelationshipType(str, Enum):
    OWNS = "OWNS"
    BELONGS_TO = "BELONGS_TO"
    BILLS = "BILLS"
    PAYS = "PAYS"
    RECORDS = "RECORDS"
    POSTS_TO = "POSTS_TO"
    SETTLES = "SETTLES"
    ALLOCATES_TO = "ALLOCATES_TO"
    REPORTS_TO = "REPORTS_TO"


@dataclass(frozen=True)
class AccountingObjectRule:
    object_type: AccountingObjectType
    base_object: str = "EnterpriseObject"
    relationship_engine: str = "EnterpriseKnowledgeGraph"
    reusable_across_verticals: bool = True


@dataclass(frozen=True)
class AccountTypeRule:
    account_type: AccountType
    normal_balance: NormalBalance


@dataclass(frozen=True)
class EnterpriseAccountingArchitecture:
    architecture_code: str = "EAA-001A"
    name: str = "Standard Enterprise Accounting Architecture"
    standard: str = "Double-entry accounting"
    kernel: str = "EnterpriseKernel"
    graph: str = "EnterpriseKnowledgeGraph"
    object_base: str = "EnterpriseObject"
    currency_default: str = "IDR"
    principles: tuple[str, ...] = (
        "Accounting must follow standard accounting principles",
        "Every transaction must use double-entry accounting",
        "Every journal entry must balance debit and credit",
        "Every accounting object is an EnterpriseObject",
        "Every accounting relationship is stored in the Enterprise Knowledge Graph",
        "Income and expense are not raw cash movements",
        "Cash in may represent revenue, receivable settlement, capital injection, or debt",
        "Cash out may represent expense, asset purchase, debt payment, or owner distribution",
        "FIN modules must not create duplicate accounting engines",
    )
    account_type_rules: tuple[AccountTypeRule, ...] = (
        AccountTypeRule(AccountType.ASSET, NormalBalance.DEBIT),
        AccountTypeRule(AccountType.EXPENSE, NormalBalance.DEBIT),
        AccountTypeRule(AccountType.LIABILITY, NormalBalance.CREDIT),
        AccountTypeRule(AccountType.EQUITY, NormalBalance.CREDIT),
        AccountTypeRule(AccountType.REVENUE, NormalBalance.CREDIT),
    )
    object_rules: tuple[AccountingObjectRule, ...] = field(
        default_factory=lambda: tuple(
            AccountingObjectRule(object_type=obj_type)
            for obj_type in AccountingObjectType
        )
    )
    relationship_types: tuple[AccountingRelationshipType, ...] = tuple(AccountingRelationshipType)

    def validate(self) -> bool:
        if self.kernel != "EnterpriseKernel":
            return False
        if self.graph != "EnterpriseKnowledgeGraph":
            return False
        if self.object_base != "EnterpriseObject":
            return False
        if self.standard != "Double-entry accounting":
            return False
        return all(
            rule.base_object == "EnterpriseObject"
            and rule.relationship_engine == "EnterpriseKnowledgeGraph"
            and rule.reusable_across_verticals
            for rule in self.object_rules
        )

    def normal_balance_for(self, account_type: AccountType) -> NormalBalance:
        for rule in self.account_type_rules:
            if rule.account_type == account_type:
                return rule.normal_balance
        raise ValueError(f"Unknown account type: {account_type}")

    def object_type_names(self) -> list[str]:
        return [rule.object_type.value for rule in self.object_rules]

    def relationship_type_names(self) -> list[str]:
        return [relationship.value for relationship in self.relationship_types]

from dataclasses import dataclass, field
from enum import Enum


class AccountingObjectType(str, Enum):
    COMPANY = "COMPANY"
    PROJECT = "PROJECT"
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    ACCOUNT = "ACCOUNT"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    LEDGER_ENTRY = "LEDGER_ENTRY"
    INVOICE = "INVOICE"
    PAYMENT = "PAYMENT"
    EXPENSE = "EXPENSE"
    TAX = "TAX"
    BUDGET = "BUDGET"


class AccountingRelationshipType(str, Enum):
    OWNS = "OWNS"
    BELONGS_TO = "BELONGS_TO"
    FUNDS = "FUNDS"
    BILLS = "BILLS"
    PAYS = "PAYS"
    RECORDS = "RECORDS"
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
class EnterpriseAccountingArchitecture:
    architecture_code: str = "EAA-001"
    name: str = "Enterprise Accounting Architecture"
    kernel: str = "EnterpriseKernel"
    graph: str = "EnterpriseKnowledgeGraph"
    object_base: str = "EnterpriseObject"
    currency_default: str = "IDR"
    principles: tuple[str, ...] = (
        "Every accounting object is an EnterpriseObject",
        "Every accounting relationship is stored in the Enterprise Knowledge Graph",
        "Accounting is reusable across all AI5R verticals",
        "Company, project, finance, sales, inventory, HR, and dashboard data share one enterprise accounting language",
        "FIN modules must not create duplicate accounting engines",
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
        return all(
            rule.base_object == "EnterpriseObject"
            and rule.relationship_engine == "EnterpriseKnowledgeGraph"
            and rule.reusable_across_verticals
            for rule in self.object_rules
        )

    def object_type_names(self) -> list[str]:
        return [rule.object_type.value for rule in self.object_rules]

    def relationship_type_names(self) -> list[str]:
        return [relationship.value for relationship in self.relationship_types]

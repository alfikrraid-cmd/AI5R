from dataclasses import dataclass
from enum import Enum


class EnterpriseOperatingLayer(str, Enum):
    OBJECT = "ENTERPRISE_OBJECT"
    EVENT = "ENTERPRISE_EVENT"
    DOCUMENT = "ENTERPRISE_DOCUMENT"
    WORKFLOW = "ENTERPRISE_WORKFLOW"
    TRANSACTION = "ENTERPRISE_TRANSACTION"
    ACCOUNTING = "ENTERPRISE_ACCOUNTING"
    EXECUTIVE_INTELLIGENCE = "EXECUTIVE_INTELLIGENCE"


@dataclass(frozen=True)
class EnterpriseOperatingStack:
    stack_code: str = "ENT-003"
    name: str = "Enterprise Operating Stack"
    layers: tuple[EnterpriseOperatingLayer, ...] = (
        EnterpriseOperatingLayer.OBJECT,
        EnterpriseOperatingLayer.EVENT,
        EnterpriseOperatingLayer.DOCUMENT,
        EnterpriseOperatingLayer.WORKFLOW,
        EnterpriseOperatingLayer.TRANSACTION,
        EnterpriseOperatingLayer.ACCOUNTING,
        EnterpriseOperatingLayer.EXECUTIVE_INTELLIGENCE,
    )
    principles: tuple[str, ...] = (
        "Every business object must use EnterpriseObject",
        "Every business change must emit EnterpriseEvent",
        "Every business process starts from EnterpriseDocument",
        "Every EnterpriseDocument must pass through EnterpriseWorkflow",
        "Only completed workflows may produce EnterpriseTransaction",
        "No vertical module may create journal entries directly",
        "Only EnterpriseAccounting may translate transactions into journal entries",
        "Executive Intelligence consumes enterprise data, not duplicated vertical data",
    )

    def validate(self) -> bool:
        return self.layers == (
            EnterpriseOperatingLayer.OBJECT,
            EnterpriseOperatingLayer.EVENT,
            EnterpriseOperatingLayer.DOCUMENT,
            EnterpriseOperatingLayer.WORKFLOW,
            EnterpriseOperatingLayer.TRANSACTION,
            EnterpriseOperatingLayer.ACCOUNTING,
            EnterpriseOperatingLayer.EXECUTIVE_INTELLIGENCE,
        )

    def layer_names(self) -> list[str]:
        return [layer.value for layer in self.layers]

    def allows_direct_journal_from_vertical(self) -> bool:
        return False

    def accounting_entry_source(self) -> str:
        return EnterpriseOperatingLayer.TRANSACTION.value

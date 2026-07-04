from dataclasses import dataclass
from .eas_rules import RULES


@dataclass
class EnterpriseArchitectureSpecification:
    version: str = "1.0"
    status: str = "canonical"

    def rules(self):
        return RULES

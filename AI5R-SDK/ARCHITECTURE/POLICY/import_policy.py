from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PolicyViolation:
    module: str
    forbidden_import: str
    reason: str = ""


@dataclass
class ImportPolicyResult:
    violations: list[PolicyViolation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.violations) == 0


class ImportPolicyEngine:
    """
    Canonical Import Rules:

    FOUNDATION -> cannot depend on OS
    DIGITAL_EMPLOYEE -> cannot import FOUNDATION internals directly (except allowed)
    OS -> allowed to depend on everything
    """

    RULES = {
        "FOUNDATION": ["OS"],
        "DIGITAL_EMPLOYEE": [],
        "DIGITAL_WORKFLOW": [],
        "DIGITAL_ORGANIZATION": [],
        "MEMORY": [],
        "KNOWLEDGE": [],
    }

    def __init__(self, dependency_graph: dict[str, list[str]]):
        self.graph = dependency_graph

    def validate(self) -> ImportPolicyResult:
        result = ImportPolicyResult()

        for module, deps in self.graph.items():
            base = module.split(".")[0]

            forbidden = self.RULES.get(base, [])

            for dep in deps:
                dep_base = dep.split(".")[0]

                if dep_base in forbidden:
                    result.violations.append(
                        PolicyViolation(
                            module=module,
                            forbidden_import=dep,
                            reason=f"{base} cannot depend on {dep_base}",
                        )
                    )

        return result

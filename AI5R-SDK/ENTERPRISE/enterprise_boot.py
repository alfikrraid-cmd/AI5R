from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnterpriseBootResult:
    boot_steps: list[str] = field(default_factory=list)

    def add(self, step: str):
        self.boot_steps.append(step)

    @property
    def success(self) -> bool:
        return len(self.boot_steps) > 0


class EnterpriseBoot:
    def __init__(self):
        self.result = EnterpriseBootResult()

    def boot_kernel(self):
        self.result.add("kernel")

    def boot_employees(self):
        self.result.add("employees")

    def boot_organization(self):
        self.result.add("organization")

    def boot_brain(self):
        self.result.add("brain")

    def boot_workflow(self):
        self.result.add("workflow")

    def boot_os(self):
        self.result.add("os")

    def shutdown(self):
        self.result.add("shutdown")

    def full_boot(self):
        self.boot_kernel()
        self.boot_os()
        self.boot_employees()
        self.boot_organization()
        self.boot_workflow()
        self.boot_brain()
        self.shutdown()

        return self.result

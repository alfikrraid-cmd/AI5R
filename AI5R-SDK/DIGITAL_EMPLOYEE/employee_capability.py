from dataclasses import dataclass, field


@dataclass
class EmployeeCapability:
    capabilities: list[str] = field(default_factory=list)

    def add(self, capability: str):
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

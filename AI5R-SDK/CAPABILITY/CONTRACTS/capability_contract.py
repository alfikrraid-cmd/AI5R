from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapabilityManifest:
    capability_id: str
    capability_name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    brain_version: str = "1.0"
    dependencies: list[str] = field(default_factory=list)
    knowledge: list[str] = field(default_factory=list)
    workflows: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    governance: list[str] = field(default_factory=list)
    validators: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

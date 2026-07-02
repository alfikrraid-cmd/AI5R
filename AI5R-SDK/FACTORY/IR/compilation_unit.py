"""
FM-005.1 Compilation Unit
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from IR.entity_ir import EntityIR


@dataclass
class CompilationUnit:
    product: str
    entities: List[EntityIR] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_entity(self, entity: EntityIR) -> None:
        self.entities.append(entity)

    def entity_count(self) -> int:
        return len(self.entities)

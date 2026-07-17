"""
UMC-001 Universal Manufacturing Contract -- Relationship Resolution stage.

Platform interface only. Per MWO-LTSA-048 WP-000 Rev. 3 (Chief Architect
directive), Relationship Resolution remains an interface -- no concrete
resolution logic is implemented here. A Factory Pack (LTSA-BRAIN first)
implements this interface against its own canonical tables' existing
cross-references (e.g. seal_pump_compatibility, seal_interchange_compatibility,
mapping_profile/column_mapping's canonical_attribute concept).

Sits between Manufacturing Validation and Canonical Object Manufacturing in
the Universal Manufacturing Contract's stage order (see
FACTORY/CORE/universal_manufacturing_contract.py), alongside Identity
Resolution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext


@dataclass
class RelationshipResolution:
    resolved: dict[str, str] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)


class RelationshipResolver(ABC):
    """
    Given candidate relationship references by natural key, resolves each to
    a canonical foreign key or reports it unresolvable. Read-only -- must
    never mutate state.
    """

    @abstractmethod
    def resolve(
        self,
        object_type: str,
        candidate_relationships: dict[str, Any],
        context: ManufacturingContext,
    ) -> RelationshipResolution:
        raise NotImplementedError

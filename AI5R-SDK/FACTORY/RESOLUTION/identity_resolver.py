"""
UMC-001 Universal Manufacturing Contract -- Identity Resolution stage.

Platform interface only. Per MWO-LTSA-048 WP-000 Rev. 3 (Chief Architect
directive), Identity Resolution remains an interface -- no concrete
matching/deduplication logic is implemented here. A Factory Pack (LTSA-BRAIN
first) implements this interface against its own canonical tables' natural
keys (e.g. ltsa_pumps.tag_number, seal_registry.seal_code).

Sits between Manufacturing Validation and Canonical Object Manufacturing in
the Universal Manufacturing Contract's stage order (see
FACTORY/CORE/universal_manufacturing_contract.py).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext


@dataclass
class IdentityResolution:
    matched: bool
    canonical_id: str | None
    confidence: float | None


class IdentityResolver(ABC):
    """
    Given a candidate natural key, determines whether a canonical object of
    the given object_type already exists. Read-only -- must never mutate
    state.
    """

    @abstractmethod
    def resolve(
        self,
        object_type: str,
        candidate_key: dict[str, Any],
        context: ManufacturingContext,
    ) -> IdentityResolution:
        raise NotImplementedError

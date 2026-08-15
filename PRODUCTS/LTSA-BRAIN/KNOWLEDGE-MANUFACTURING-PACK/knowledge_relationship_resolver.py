"""MWO-LTSA-074 -- Relationship Resolution stage.

Reuses FACTORY.RESOLUTION.relationship_resolver.RelationshipResolver (ABC)
unmodified, the exact same reuse convention PUMP-FACTORY-PACK's own
PumpRelationshipResolver already established: constructor-injected "known"
registries, `.resolve()` performs no I/O of its own, unresolved candidates
are reported honestly, never guessed.

The one genuine difference from PumpRelationshipResolver: that resolver's
"known" registry is a live query result (e.g. all of seal_registry). This
pipeline has no database access at all ("No database writes... Pure
transformation only") -- its "known" registries are the OTHER entities
already extracted into the SAME CanonicalKnowledgePackage (e.g. an
Installation Report's own embedded pump/seal/drawing sections). Cross-
document resolution against a live canonical registry is explicitly out of
scope for this pure pipeline; it is a natural extension point for a future
MWO that wires a real Gateway's query result in as `known_pumps` etc. --
the constructor signature already accepts that shape unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext  # noqa: E402
from FACTORY.RESOLUTION.relationship_resolver import (  # noqa: E402
    RelationshipResolution,
    RelationshipResolver,
)

# object_type -> { candidate_relationship_key -> (registry_attr, registry_field) }
# Every mapping here is a real, already-established cross-reference (see this
# module's own header + knowledge_dataclasses.py's provenance notes) -- never
# an invented relationship.
_RELATIONSHIP_TARGETS: dict[str, dict[str, tuple[str, str]]] = {
    "INSTALLATION": {
        "plant_equip_no": ("known_pumps", "tag_number"),
        "drawing_no": ("known_drawings", "document_number"),
        "seal_code": ("known_seals", "seal_code"),
    },
    "DRAWING": {
        "seal_code": ("known_seals", "seal_code"),
    },
    "PM": {
        "asset_code": ("known_pumps", "tag_number"),
    },
    "CM": {
        "asset_code": ("known_pumps", "tag_number"),
    },
    "FAILURE": {
        "asset_code": ("known_pumps", "tag_number"),
        "work_order_code": ("known_workorders", "work_order_code"),
    },
    "WORKORDER": {
        "asset_code": ("known_pumps", "tag_number"),
    },
    "DOCUMENT": {
        "seal_code": ("known_seals", "seal_code"),
    },
}


class KnowledgeRelationshipResolver(RelationshipResolver):
    def __init__(
        self,
        *,
        known_pumps: list[dict[str, Any]] | None = None,
        known_seals: list[dict[str, Any]] | None = None,
        known_drawings: list[dict[str, Any]] | None = None,
        known_workorders: list[dict[str, Any]] | None = None,
    ):
        self.known_pumps = known_pumps or []
        self.known_seals = known_seals or []
        self.known_drawings = known_drawings or []
        self.known_workorders = known_workorders or []

    def resolve(
        self,
        object_type: str,
        candidate_relationships: dict[str, Any],
        context: ManufacturingContext,
    ) -> RelationshipResolution:
        targets = _RELATIONSHIP_TARGETS.get(object_type, {})

        resolved: dict[str, str] = {}
        unresolved: list[str] = []

        for key, value in candidate_relationships.items():
            target = targets.get(key)
            match = self._find(target, value) if target and value else None
            if match is not None:
                resolved[key] = match
            else:
                unresolved.append(key)

        return RelationshipResolution(resolved=resolved, unresolved=unresolved)

    def _find(self, target: tuple[str, str] | None, value: Any) -> str | None:
        if target is None:
            return None
        registry_attr, registry_field = target
        for row in getattr(self, registry_attr):
            if row.get(registry_field) == value:
                return row.get(registry_field)
        return None


_CANDIDATE_KEYS_BY_OBJECT_TYPE: dict[str, tuple[str, ...]] = {
    object_type: tuple(keys.keys()) for object_type, keys in _RELATIONSHIP_TARGETS.items()
}


def resolve_package_relationships(
    normalized: dict[str, Any],
    context: ManufacturingContext | None = None,
) -> RelationshipResolution:
    """Convenience orchestration over the ABC's single-object_type
    `.resolve()`: builds a KnowledgeRelationshipResolver from the package's
    OWN sibling entities (never a live DB query, per this pipeline's "no
    database writes" scope), then resolves every entity present in the
    normalized extraction, merging into one RelationshipResolution for the
    whole CanonicalKnowledgePackage."""
    context = context or ManufacturingContext(build_id="knowledge-manufacturing-pack", product="LTSA", version="1")

    resolver = KnowledgeRelationshipResolver(
        known_pumps=[normalized["pump"]] if normalized.get("pump") else [],
        known_seals=[normalized["seal"]] if normalized.get("seal") else [],
        known_drawings=[normalized["drawing"]] if normalized.get("drawing") else [],
        known_workorders=list(normalized.get("workorder") or []),
    )

    resolved: dict[str, str] = {}
    unresolved: list[str] = []

    def _run(object_type: str, data: dict[str, Any] | None) -> None:
        if not data:
            return
        candidate_keys = _CANDIDATE_KEYS_BY_OBJECT_TYPE.get(object_type, ())
        candidates = {key: data.get(key) for key in candidate_keys if data.get(key)}
        if not candidates:
            return
        result = resolver.resolve(object_type, candidates, context)
        resolved.update(result.resolved)
        unresolved.extend(result.unresolved)

    _run("INSTALLATION", normalized.get("installation"))
    _run("DRAWING", normalized.get("drawing"))
    for pm in normalized.get("pm") or []:
        _run("PM", pm)
    for cm in normalized.get("cm") or []:
        _run("CM", cm)
    for failure in normalized.get("failure") or []:
        _run("FAILURE", failure)
    for workorder in normalized.get("workorder") or []:
        _run("WORKORDER", workorder)
    for document in normalized.get("documents") or []:
        _run("DOCUMENT", document)

    return RelationshipResolution(resolved=resolved, unresolved=unresolved)

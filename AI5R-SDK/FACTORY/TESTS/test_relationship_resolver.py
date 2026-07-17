import pytest

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext
from FACTORY.RESOLUTION.relationship_resolver import (
    RelationshipResolution,
    RelationshipResolver,
)


def test_relationship_resolver_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        RelationshipResolver()


def test_concrete_relationship_resolver_satisfies_the_interface():
    class StubRelationshipResolver(RelationshipResolver):
        def resolve(self, object_type, candidate_relationships, context):
            return RelationshipResolution(
                resolved={"seal_type": "SC-9"},
                unresolved=[],
            )

    context = ManufacturingContext(build_id="BUILD-1", product="LTSA-BRAIN", version="1.0")
    result = StubRelationshipResolver().resolve(
        "PUMP_COMPATIBILITY", {"seal_type": "Type 21"}, context
    )

    assert isinstance(result, RelationshipResolution)
    assert result.resolved == {"seal_type": "SC-9"}
    assert result.unresolved == []


def test_relationship_resolution_defaults_are_empty():
    resolution = RelationshipResolution()

    assert resolution.resolved == {}
    assert resolution.unresolved == []

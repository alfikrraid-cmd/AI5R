import pytest

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext
from FACTORY.RESOLUTION.identity_resolver import IdentityResolution, IdentityResolver


def test_identity_resolver_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        IdentityResolver()


def test_concrete_identity_resolver_satisfies_the_interface():
    class StubIdentityResolver(IdentityResolver):
        def resolve(self, object_type, candidate_key, context):
            return IdentityResolution(matched=True, canonical_id="P-101", confidence=1.0)

    context = ManufacturingContext(build_id="BUILD-1", product="LTSA-BRAIN", version="1.0")
    result = StubIdentityResolver().resolve("PUMP", {"tag_number": "P-101"}, context)

    assert isinstance(result, IdentityResolution)
    assert result.matched is True
    assert result.canonical_id == "P-101"

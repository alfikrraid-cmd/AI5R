import pytest

from FACTORY.PACKS.factory_pack import FactoryPack


def test_factory_pack_contract_validates():
    pack = FactoryPack(
        pack_code="FP-WEBSITE-001",
        pack_name="Website Factory Pack",
        product_type="WEBSITE",
        capabilities=["GENERATE_HTML", "GENERATE_COPY"],
        recipe_path="PRODUCTS/WEBSITE/recipe.json",
    )

    assert pack.validate() is True


def test_factory_pack_requires_capabilities():
    pack = FactoryPack(
        pack_code="FP-WEBSITE-001",
        pack_name="Website Factory Pack",
        product_type="WEBSITE",
        capabilities=[],
        recipe_path="PRODUCTS/WEBSITE/recipe.json",
    )

    with pytest.raises(ValueError):
        pack.validate()

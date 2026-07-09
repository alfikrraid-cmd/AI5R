from FACTORY.PACKS.CONTRACTS.pack_contract import FactoryPackContract
from FACTORY.PACKS.CONTRACTS.validator import FactoryPackValidator


def test_factory_pack_contract():

    contract = FactoryPackContract(
        pack_id="FP-FASTAPI-001",
        pack_name="FastAPI Service Pack",
        version="1.0.0",
        product_type="FASTAPI_SERVICE",
        blueprint="blueprint.yaml",
        recipe="recipe.yaml",
        templates_path="templates",
        validation_module="validation.py",
        manifest_path="manifest.json",
    )

    assert FactoryPackValidator().validate(contract)

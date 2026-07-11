import json
import sys

import pytest


def make_architecture(**overrides):
    defaults = dict(
        architecture_name="WO-200",
        product_name="Payments Platform",
        modules=["ROLE-BACKEND", "ROLE-DATABASE"],
        services=["billing-service"],
        apis=["/api/v1/payments"],
        database=["payments_db"],
        constraints=["budget<=200000"],
        priority="HIGH",
    )
    defaults.update(overrides)
    return defaults


def test_manufacture_accepts_valid_architecture():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert isinstance(result, dict)


def test_manufacture_rejects_non_dict_architecture():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()

    with pytest.raises(ValueError):
        pack.manufacture(None)


def test_manufacture_rejects_missing_architecture_name():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()
    del architecture["architecture_name"]

    with pytest.raises(ValueError):
        pack.manufacture(architecture)


def test_manufacture_rejects_missing_product_name():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()
    del architecture["product_name"]

    with pytest.raises(ValueError):
        pack.manufacture(architecture)


def test_manufacture_is_deterministic():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()

    first = pack.manufacture(architecture)
    second = pack.manufacture(architecture)

    assert first == second


def test_manufacture_returns_required_files():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert set(result.keys()) == {
        "openapi.json",
        "routes.json",
        "api.manifest.json",
        "README_API.md",
    }
    assert isinstance(result["openapi.json"], str) and result["openapi.json"]
    assert isinstance(result["routes.json"], str) and result["routes.json"]
    assert isinstance(result["api.manifest.json"], dict)
    assert isinstance(result["README_API.md"], str) and result["README_API.md"]


def test_manufacture_openapi_json_is_valid_json_with_declared_paths():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)
    openapi = json.loads(result["openapi.json"])

    assert openapi["info"]["title"] == "Payments Platform"
    assert "/api/v1/payments" in openapi["paths"]


def test_manufacture_routes_json_is_valid_json_with_declared_routes():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)
    routes = json.loads(result["routes.json"])

    paths = [route["path"] for route in routes["routes"]]
    assert "/api/v1/payments" in paths


def test_manufacture_readme_contains_product_name():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert "Payments Platform" in result["README_API.md"]


def test_manufacture_manifest_correctness():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)
    manifest = result["api.manifest.json"]

    assert manifest == {
        "pack": "API",
        "architecture_name": "WO-200",
        "product_name": "Payments Platform",
        "modules": ["ROLE-BACKEND", "ROLE-DATABASE"],
        "services": ["billing-service"],
        "apis": ["/api/v1/payments"],
        "database": ["payments_db"],
        "constraints": ["budget<=200000"],
        "priority": "HIGH",
        "files": ["openapi.json", "routes.json", "README_API.md"],
    }


def test_manufacture_defaults_optional_fields_to_empty():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = {
        "architecture_name": "WO-201",
        "product_name": "Minimal Product",
    }

    result = pack.manufacture(architecture)
    manifest = result["api.manifest.json"]

    assert manifest["modules"] == []
    assert manifest["services"] == []
    assert manifest["apis"] == []
    assert manifest["database"] == []
    assert manifest["constraints"] == []
    assert manifest["priority"] == "NORMAL"


def test_manufacture_output_is_immutable_from_input_mutation():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)
    architecture["modules"].append("ROLE-EXTRA")

    assert result["api.manifest.json"]["modules"] == [
        "ROLE-BACKEND",
        "ROLE-DATABASE",
    ]


def test_stateless_across_calls():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    pack = ApiFactoryPack()
    first_architecture = make_architecture(architecture_name="WO-A")
    second_architecture = make_architecture(architecture_name="WO-B")

    pack.manufacture(first_architecture)
    second_result = pack.manufacture(second_architecture)

    assert second_result["api.manifest.json"]["architecture_name"] == "WO-B"
    assert pack.manufacture(first_architecture) == pack.manufacture(first_architecture)


def test_stateless_between_independent_instances():
    from FACTORY_PACKS.API.api_factory_pack import ApiFactoryPack

    first_pack = ApiFactoryPack()
    second_pack = ApiFactoryPack()
    architecture = make_architecture()

    assert first_pack.manufacture(architecture) == second_pack.manufacture(architecture)


def test_api_factory_pack_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import FACTORY_PACKS.API.api_factory_pack  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER") for module_name in sys.modules
    )


def test_api_factory_pack_is_independent_of_organization():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION"):
            del sys.modules[module_name]

    import FACTORY_PACKS.API.api_factory_pack  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION") for module_name in sys.modules
    )


def test_api_factory_pack_is_independent_of_runtime():
    for module_name in list(sys.modules):
        if module_name.startswith("RUNTIME"):
            del sys.modules[module_name]

    import FACTORY_PACKS.API.api_factory_pack  # noqa: F401

    assert not any(
        module_name.startswith("RUNTIME") for module_name in sys.modules
    )

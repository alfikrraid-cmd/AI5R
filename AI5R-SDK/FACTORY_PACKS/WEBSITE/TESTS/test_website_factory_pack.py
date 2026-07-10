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
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert isinstance(result, dict)


def test_manufacture_rejects_non_dict_architecture():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()

    with pytest.raises(ValueError):
        pack.manufacture(None)


def test_manufacture_rejects_missing_architecture_name():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = make_architecture()
    del architecture["architecture_name"]

    with pytest.raises(ValueError):
        pack.manufacture(architecture)


def test_manufacture_rejects_missing_product_name():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = make_architecture()
    del architecture["product_name"]

    with pytest.raises(ValueError):
        pack.manufacture(architecture)


def test_manufacture_is_deterministic():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = make_architecture()

    first = pack.manufacture(architecture)
    second = pack.manufacture(architecture)

    assert first == second


def test_manufacture_returns_required_files():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert set(result.keys()) == {
        "index.html",
        "style.css",
        "app.js",
        "README.md",
        "website.manifest.json",
    }
    assert isinstance(result["index.html"], str) and result["index.html"]
    assert isinstance(result["style.css"], str) and result["style.css"]
    assert isinstance(result["app.js"], str) and result["app.js"]
    assert isinstance(result["README.md"], str) and result["README.md"]
    assert isinstance(result["website.manifest.json"], dict)


def test_manufacture_index_html_contains_product_name():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert "Payments Platform" in result["index.html"]


def test_manufacture_manifest_correctness():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)
    manifest = result["website.manifest.json"]

    assert manifest == {
        "pack": "WEBSITE",
        "architecture_name": "WO-200",
        "product_name": "Payments Platform",
        "modules": ["ROLE-BACKEND", "ROLE-DATABASE"],
        "services": ["billing-service"],
        "apis": ["/api/v1/payments"],
        "database": ["payments_db"],
        "constraints": ["budget<=200000"],
        "priority": "HIGH",
        "files": ["index.html", "style.css", "app.js", "README.md"],
    }


def test_manufacture_defaults_optional_fields_to_empty():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = {
        "architecture_name": "WO-201",
        "product_name": "Minimal Product",
    }

    result = pack.manufacture(architecture)
    manifest = result["website.manifest.json"]

    assert manifest["modules"] == []
    assert manifest["services"] == []
    assert manifest["apis"] == []
    assert manifest["database"] == []
    assert manifest["constraints"] == []
    assert manifest["priority"] == "NORMAL"


def test_manufacture_output_is_immutable_from_input_mutation():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)
    architecture["modules"].append("ROLE-EXTRA")

    assert result["website.manifest.json"]["modules"] == [
        "ROLE-BACKEND",
        "ROLE-DATABASE",
    ]


def test_stateless_across_calls():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    pack = WebsiteFactoryPack()
    first_architecture = make_architecture(architecture_name="WO-A")
    second_architecture = make_architecture(architecture_name="WO-B")

    pack.manufacture(first_architecture)
    second_result = pack.manufacture(second_architecture)

    assert second_result["website.manifest.json"]["architecture_name"] == "WO-B"
    assert pack.manufacture(first_architecture) == pack.manufacture(first_architecture)


def test_stateless_between_independent_instances():
    from FACTORY_PACKS.WEBSITE.website_factory_pack import WebsiteFactoryPack

    first_pack = WebsiteFactoryPack()
    second_pack = WebsiteFactoryPack()
    architecture = make_architecture()

    assert first_pack.manufacture(architecture) == second_pack.manufacture(
        architecture
    )


def test_website_factory_pack_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import FACTORY_PACKS.WEBSITE.website_factory_pack  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )


def test_website_factory_pack_is_independent_of_organization():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION"):
            del sys.modules[module_name]

    import FACTORY_PACKS.WEBSITE.website_factory_pack  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION") for module_name in sys.modules
    )

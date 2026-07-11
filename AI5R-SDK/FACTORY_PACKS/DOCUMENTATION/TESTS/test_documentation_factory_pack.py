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
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert isinstance(result, dict)


def test_manufacture_rejects_non_dict_architecture():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()

    with pytest.raises(ValueError):
        pack.manufacture(None)


def test_manufacture_rejects_missing_architecture_name():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()
    del architecture["architecture_name"]

    with pytest.raises(ValueError):
        pack.manufacture(architecture)


def test_manufacture_rejects_missing_product_name():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()
    del architecture["product_name"]

    with pytest.raises(ValueError):
        pack.manufacture(architecture)


def test_manufacture_is_deterministic():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()

    first = pack.manufacture(architecture)
    second = pack.manufacture(architecture)

    assert first == second


def test_manufacture_returns_required_files():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert set(result.keys()) == {
        "README.md",
        "INSTALL.md",
        "SYSTEM_OVERVIEW.md",
        "CHANGELOG.md",
        "documentation.manifest.json",
    }
    assert isinstance(result["README.md"], str) and result["README.md"]
    assert isinstance(result["INSTALL.md"], str) and result["INSTALL.md"]
    assert isinstance(result["SYSTEM_OVERVIEW.md"], str) and result["SYSTEM_OVERVIEW.md"]
    assert isinstance(result["CHANGELOG.md"], str) and result["CHANGELOG.md"]
    assert isinstance(result["documentation.manifest.json"], dict)


def test_manufacture_readme_contains_product_name():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert "Payments Platform" in result["README.md"]


def test_manufacture_system_overview_contains_modules_and_services():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)

    assert "ROLE-BACKEND" in result["SYSTEM_OVERVIEW.md"]
    assert "billing-service" in result["SYSTEM_OVERVIEW.md"]


def test_manufacture_manifest_correctness():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)
    manifest = result["documentation.manifest.json"]

    assert manifest == {
        "pack": "DOCUMENTATION",
        "architecture_name": "WO-200",
        "product_name": "Payments Platform",
        "modules": ["ROLE-BACKEND", "ROLE-DATABASE"],
        "services": ["billing-service"],
        "apis": ["/api/v1/payments"],
        "database": ["payments_db"],
        "constraints": ["budget<=200000"],
        "priority": "HIGH",
        "files": ["README.md", "INSTALL.md", "SYSTEM_OVERVIEW.md", "CHANGELOG.md"],
    }


def test_manufacture_defaults_optional_fields_to_empty():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = {
        "architecture_name": "WO-201",
        "product_name": "Minimal Product",
    }

    result = pack.manufacture(architecture)
    manifest = result["documentation.manifest.json"]

    assert manifest["modules"] == []
    assert manifest["services"] == []
    assert manifest["apis"] == []
    assert manifest["database"] == []
    assert manifest["constraints"] == []
    assert manifest["priority"] == "NORMAL"


def test_manufacture_output_is_immutable_from_input_mutation():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    architecture = make_architecture()

    result = pack.manufacture(architecture)
    architecture["modules"].append("ROLE-EXTRA")

    assert result["documentation.manifest.json"]["modules"] == [
        "ROLE-BACKEND",
        "ROLE-DATABASE",
    ]


def test_stateless_across_calls():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    pack = DocumentationFactoryPack()
    first_architecture = make_architecture(architecture_name="WO-A")
    second_architecture = make_architecture(architecture_name="WO-B")

    pack.manufacture(first_architecture)
    second_result = pack.manufacture(second_architecture)

    assert second_result["documentation.manifest.json"]["architecture_name"] == "WO-B"
    assert pack.manufacture(first_architecture) == pack.manufacture(first_architecture)


def test_stateless_between_independent_instances():
    from FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack import (
        DocumentationFactoryPack,
    )

    first_pack = DocumentationFactoryPack()
    second_pack = DocumentationFactoryPack()
    architecture = make_architecture()

    assert first_pack.manufacture(architecture) == second_pack.manufacture(architecture)


def test_documentation_factory_pack_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER") for module_name in sys.modules
    )


def test_documentation_factory_pack_is_independent_of_organization():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION"):
            del sys.modules[module_name]

    import FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION") for module_name in sys.modules
    )


def test_documentation_factory_pack_is_independent_of_runtime():
    for module_name in list(sys.modules):
        if module_name.startswith("RUNTIME"):
            del sys.modules[module_name]

    import FACTORY_PACKS.DOCUMENTATION.documentation_factory_pack  # noqa: F401

    assert not any(
        module_name.startswith("RUNTIME") for module_name in sys.modules
    )

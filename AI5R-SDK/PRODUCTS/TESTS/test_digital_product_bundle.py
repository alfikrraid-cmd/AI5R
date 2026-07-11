import sys

import pytest


def make_artifacts(**overrides):
    defaults = dict(
        website={"index.html": "<html></html>"},
        api={"openapi.json": "{}"},
        docs={"README.md": "# Docs"},
        tests={"tests/test_smoke.py": "def test_ok(): pass"},
    )
    defaults.update(overrides)
    return defaults


def test_bundle_accepts_valid_inputs():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()
    artifacts = make_artifacts()

    result = bundle.bundle("Payments Platform", artifacts)

    assert isinstance(result, dict)


def test_bundle_rejects_non_string_product_name():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()
    artifacts = make_artifacts()

    with pytest.raises(ValueError):
        bundle.bundle(None, artifacts)


def test_bundle_rejects_empty_product_name():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()
    artifacts = make_artifacts()

    with pytest.raises(ValueError):
        bundle.bundle("   ", artifacts)


def test_bundle_rejects_non_dict_artifacts():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()

    with pytest.raises(ValueError):
        bundle.bundle("Payments Platform", None)


def test_bundle_rejects_non_dict_artifacts_list():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()

    with pytest.raises(ValueError):
        bundle.bundle("Payments Platform", ["not", "a", "dict"])


def test_bundle_is_deterministic():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()
    artifacts = make_artifacts()

    first = bundle.bundle("Payments Platform", artifacts)
    second = bundle.bundle("Payments Platform", artifacts)

    assert first == second


def test_bundle_returns_required_sections():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()
    artifacts = make_artifacts()

    result = bundle.bundle("Payments Platform", artifacts)

    assert set(result.keys()) == {"manifest.json", "website", "api", "docs", "tests"}
    assert result["website"] == artifacts["website"]
    assert result["api"] == artifacts["api"]
    assert result["docs"] == artifacts["docs"]
    assert result["tests"] == artifacts["tests"]


def test_bundle_defaults_missing_sections_to_empty_dict():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()

    result = bundle.bundle("Payments Platform", {"website": {"index.html": "<html></html>"}})

    assert result["website"] == {"index.html": "<html></html>"}
    assert result["api"] == {}
    assert result["docs"] == {}
    assert result["tests"] == {}


def test_bundle_manifest_correctness():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()
    artifacts = make_artifacts()

    result = bundle.bundle("Payments Platform", artifacts)
    manifest = result["manifest.json"]

    assert manifest == {
        "product_name": "Payments Platform",
        "generated_at": None,
        "artifact_count": 4,
        "bundle_version": "1.0",
    }


def test_bundle_manifest_artifact_count_matches_provided_sections():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()

    result = bundle.bundle("Payments Platform", {"website": {}, "api": {}})
    manifest = result["manifest.json"]

    assert manifest["artifact_count"] == 2


def test_bundle_output_is_immutable_from_input_mutation():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()
    artifacts = make_artifacts()

    result = bundle.bundle("Payments Platform", artifacts)
    artifacts["website"]["index.html"] = "MUTATED"
    artifacts["extra"] = {"new": "value"}

    assert result["website"] == {"index.html": "<html></html>"}
    assert "extra" not in result


def test_stateless_across_calls():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    bundle = DigitalProductBundle()
    first_artifacts = make_artifacts(website={"a.html": "A"})
    second_artifacts = make_artifacts(website={"b.html": "B"})

    bundle.bundle("Product A", first_artifacts)
    second_result = bundle.bundle("Product B", second_artifacts)

    assert second_result["manifest.json"]["product_name"] == "Product B"
    assert second_result["website"] == {"b.html": "B"}
    assert bundle.bundle("Product A", first_artifacts) == bundle.bundle(
        "Product A", first_artifacts
    )


def test_stateless_between_independent_instances():
    from PRODUCTS.digital_product_bundle import DigitalProductBundle

    first_bundle = DigitalProductBundle()
    second_bundle = DigitalProductBundle()
    artifacts = make_artifacts()

    assert first_bundle.bundle("Payments Platform", artifacts) == second_bundle.bundle(
        "Payments Platform", artifacts
    )


def test_digital_product_bundle_is_independent_of_manufacturing():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING"):
            del sys.modules[module_name]

    import PRODUCTS.digital_product_bundle  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING") for module_name in sys.modules
    )


def test_digital_product_bundle_is_independent_of_organization():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION"):
            del sys.modules[module_name]

    import PRODUCTS.digital_product_bundle  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION") for module_name in sys.modules
    )


def test_digital_product_bundle_is_independent_of_executive():
    for module_name in list(sys.modules):
        if module_name.startswith("HEADQUARTERS"):
            del sys.modules[module_name]

    import PRODUCTS.digital_product_bundle  # noqa: F401

    assert not any(
        module_name.startswith("HEADQUARTERS") for module_name in sys.modules
    )

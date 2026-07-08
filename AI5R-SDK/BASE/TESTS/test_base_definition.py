from BASE import BaseDefinition


def test_base_definition_is_valid():
    definition = BaseDefinition(
        definition_id="DEF-001",
        definition_name="Website Recipe",
    )

    assert definition.validate_base() is True


def test_base_definition_rejects_missing_id():
    definition = BaseDefinition(
        definition_id="",
        definition_name="Website Recipe",
    )

    assert definition.validate_base() is False


def test_base_definition_rejects_missing_name():
    definition = BaseDefinition(
        definition_id="DEF-002",
        definition_name="",
    )

    assert definition.validate_base() is False


def test_base_definition_has_default_version():
    definition = BaseDefinition(
        definition_id="DEF-003",
        definition_name="ERP Recipe",
    )

    assert definition.version == "1.0.0"


def test_base_definition_accepts_metadata():
    definition = BaseDefinition(
        definition_id="DEF-004",
        definition_name="AI Agent Recipe",
        metadata={
            "product_type": "AI_AGENT",
        },
    )

    assert definition.metadata["product_type"] == "AI_AGENT"

from RUNTIME import RuntimeCapability


def test_runtime_capability_is_valid():
    capability = RuntimeCapability(
        capability_id="REQUIREMENT_ANALYSIS",
        capability_name="Requirement Analysis",
    )

    assert capability.validate() is True


def test_runtime_capability_requires_id():
    capability = RuntimeCapability(
        capability_id="",
        capability_name="Requirement Analysis",
    )

    assert capability.validate() is False


def test_runtime_capability_requires_name():
    capability = RuntimeCapability(
        capability_id="REQUIREMENT_ANALYSIS",
        capability_name="",
    )

    assert capability.validate() is False


def test_runtime_capability_has_qualified_id():
    capability = RuntimeCapability(
        capability_id="ARCHITECTURE_DESIGN",
        capability_name="Architecture Design",
        version="1.2.0",
    )

    assert capability.qualified_id() == "ARCHITECTURE_DESIGN@1.2.0"


def test_runtime_capability_accepts_contracts():
    capability = RuntimeCapability(
        capability_id="QA_VALIDATION",
        capability_name="QA Validation",
        input_contract={
            "requires": ["artifact"],
        },
        output_contract={
            "produces": ["qa_report"],
        },
    )

    assert capability.input_contract["requires"] == ["artifact"]
    assert capability.output_contract["produces"] == ["qa_report"]

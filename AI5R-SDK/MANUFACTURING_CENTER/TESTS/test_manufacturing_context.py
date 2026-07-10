from pathlib import Path

import pytest

from MANUFACTURING_CENTER.manufacturing_context import ManufacturingContext


def make_context(tmp_path: Path) -> ManufacturingContext:
    return ManufacturingContext(
        manufacturing_id=" MFG-001 ",
        mwo={"objective": "build product"},
        product_name=" LTSA ",
        factory=" Digital Factory ",
        runtime=" Python ",
        workspace=tmp_path,
        variables={"stage": "planning"},
        metadata={"owner": "Maya"},
    )


def test_create_context(tmp_path: Path):
    context = make_context(tmp_path)

    assert context.manufacturing_id == "MFG-001"
    assert context.product_name == "LTSA"
    assert context.factory == "Digital Factory"
    assert context.runtime == "Python"
    assert context.workspace == tmp_path


def test_copies_input_dictionaries(tmp_path: Path):
    mwo = {"objective": "build"}
    variables = {"stage": "planning"}
    metadata = {"owner": "Maya"}

    context = ManufacturingContext(
        manufacturing_id="MFG-001",
        mwo=mwo,
        product_name="LTSA",
        factory="Digital Factory",
        runtime="Python",
        workspace=tmp_path,
        variables=variables,
        metadata=metadata,
    )

    mwo["objective"] = "changed"
    variables["stage"] = "changed"
    metadata["owner"] = "changed"

    assert context.mwo == {"objective": "build"}
    assert context.variables == {"stage": "planning"}
    assert context.metadata == {"owner": "Maya"}


@pytest.mark.parametrize(
    ("field_name", "overrides", "message"),
    [
        (
            "manufacturing_id",
            {"manufacturing_id": " "},
            "manufacturing_id must not be empty",
        ),
        (
            "mwo",
            {"mwo": {}},
            "mwo must not be empty",
        ),
        (
            "product_name",
            {"product_name": " "},
            "product_name must not be empty",
        ),
        (
            "factory",
            {"factory": " "},
            "factory must not be empty",
        ),
        (
            "runtime",
            {"runtime": " "},
            "runtime must not be empty",
        ),
    ],
)
def test_rejects_invalid_required_fields(
    tmp_path: Path,
    field_name: str,
    overrides: dict,
    message: str,
):
    values = {
        "manufacturing_id": "MFG-001",
        "mwo": {"objective": "build"},
        "product_name": "LTSA",
        "factory": "Digital Factory",
        "runtime": "Python",
        "workspace": tmp_path,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        ManufacturingContext(**values)


def test_workspace_must_be_path():
    with pytest.raises(TypeError, match="workspace must be a Path"):
        ManufacturingContext(
            manufacturing_id="MFG-001",
            mwo={"objective": "build"},
            product_name="LTSA",
            factory="Digital Factory",
            runtime="Python",
            workspace="/tmp/ai5r",
        )


def test_workspace_must_be_absolute():
    with pytest.raises(
        ValueError,
        match="workspace must be an absolute path",
    ):
        ManufacturingContext(
            manufacturing_id="MFG-001",
            mwo={"objective": "build"},
            product_name="LTSA",
            factory="Digital Factory",
            runtime="Python",
            workspace=Path("relative/path"),
        )


def test_set_and_get_variable(tmp_path: Path):
    context = make_context(tmp_path)

    context.set_variable(" progress ", 75)

    assert context.get_variable("progress") == 75
    assert context.get_variable("missing", "fallback") == "fallback"


def test_rejects_empty_variable_name(tmp_path: Path):
    context = make_context(tmp_path)

    with pytest.raises(
        ValueError,
        match="variable name must not be empty",
    ):
        context.set_variable(" ", 1)


def test_update_metadata(tmp_path: Path):
    context = make_context(tmp_path)

    context.update_metadata(
        {
            " priority ": "high",
            "sprint": "MFG-001",
        }
    )

    assert context.metadata["priority"] == "high"
    assert context.metadata["sprint"] == "MFG-001"


def test_rejects_empty_metadata_key(tmp_path: Path):
    context = make_context(tmp_path)

    with pytest.raises(
        ValueError,
        match="metadata key must not be empty",
    ):
        context.update_metadata({" ": "invalid"})


def test_rejects_non_string_metadata_key(tmp_path: Path):
    context = make_context(tmp_path)

    with pytest.raises(
        TypeError,
        match="metadata key must be a string",
    ):
        context.update_metadata({1: "invalid"})


def test_workspace_exists(tmp_path: Path):
    context = make_context(tmp_path)

    assert context.workspace_exists is True

    missing_path = tmp_path / "missing"
    missing_context = ManufacturingContext(
        manufacturing_id="MFG-002",
        mwo={"objective": "build"},
        product_name="LTSA",
        factory="Digital Factory",
        runtime="Python",
        workspace=missing_path,
    )

    assert missing_context.workspace_exists is False

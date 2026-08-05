"""
MWO-RAE-000E -- ParsedModule: pure immutable evidence value object. No
parser logic, no serialization -- these tests only verify the object's
own construction/immutability/equality/hashability contract.
"""

import dataclasses
from pathlib import Path

import pytest

from REPOSITORY_ARCHAEOLOGY.evidence.parsed_module import ParsedModule


def test_construction_holds_all_fields():
    module = ParsedModule(
        module_name="parser_registry",
        file_path=Path("AI5R-SDK/REPOSITORY_ARCHAEOLOGY/parser_registry.py"),
        language="python",
    )

    assert module.module_name == "parser_registry"
    assert module.file_path == Path("AI5R-SDK/REPOSITORY_ARCHAEOLOGY/parser_registry.py")
    assert module.language == "python"


def test_file_path_is_a_pathlib_path():
    module = ParsedModule(module_name="m", file_path=Path("m.py"), language="python")

    assert isinstance(module.file_path, Path)


def test_immutability():
    module = ParsedModule(module_name="m", file_path=Path("m.py"), language="python")

    with pytest.raises(dataclasses.FrozenInstanceError):
        module.module_name = "changed"


def test_equality_by_value():
    a = ParsedModule(module_name="m", file_path=Path("m.py"), language="python")
    b = ParsedModule(module_name="m", file_path=Path("m.py"), language="python")

    assert a == b


def test_inequality_on_different_field():
    a = ParsedModule(module_name="m", file_path=Path("m.py"), language="python")
    b = ParsedModule(module_name="other", file_path=Path("m.py"), language="python")

    assert a != b


def test_hashability():
    a = ParsedModule(module_name="m", file_path=Path("m.py"), language="python")
    b = ParsedModule(module_name="m", file_path=Path("m.py"), language="python")

    assert hash(a) == hash(b)
    assert len({a, b}) == 1

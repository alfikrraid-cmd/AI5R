"""MWO-RAE-000E -- ParsedClass: pure immutable evidence value object."""

import dataclasses

import pytest

from REPOSITORY_ARCHAEOLOGY.evidence.parsed_class import ParsedClass


def test_construction_holds_all_fields():
    parsed = ParsedClass(
        class_name="ParserRegistry",
        module_name="parser_registry",
        base_classes=("object",),
        decorators=("dataclass",),
    )

    assert parsed.class_name == "ParserRegistry"
    assert parsed.module_name == "parser_registry"
    assert parsed.base_classes == ("object",)
    assert parsed.decorators == ("dataclass",)


def test_base_classes_and_decorators_default_to_empty_tuple():
    parsed = ParsedClass(class_name="Plain", module_name="m")

    assert parsed.base_classes == ()
    assert parsed.decorators == ()


def test_immutability():
    parsed = ParsedClass(class_name="C", module_name="m")

    with pytest.raises(dataclasses.FrozenInstanceError):
        parsed.class_name = "changed"


def test_equality_by_value():
    a = ParsedClass(class_name="C", module_name="m", base_classes=("A",), decorators=())
    b = ParsedClass(class_name="C", module_name="m", base_classes=("A",), decorators=())

    assert a == b


def test_inequality_on_different_base_classes():
    a = ParsedClass(class_name="C", module_name="m", base_classes=("A",))
    b = ParsedClass(class_name="C", module_name="m", base_classes=("B",))

    assert a != b


def test_hashability():
    a = ParsedClass(class_name="C", module_name="m", base_classes=("A",), decorators=("dec",))
    b = ParsedClass(class_name="C", module_name="m", base_classes=("A",), decorators=("dec",))

    assert hash(a) == hash(b)
    assert len({a, b}) == 1

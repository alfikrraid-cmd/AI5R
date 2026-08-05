"""MWO-RAE-000E -- ParsedFunction: pure immutable evidence value object."""

import dataclasses

import pytest

from REPOSITORY_ARCHAEOLOGY.evidence.parsed_function import ParsedFunction


def test_construction_holds_all_fields():
    parsed = ParsedFunction(
        function_name="register",
        module_name="parser_registry",
        decorators=("staticmethod",),
        arguments=("self", "registration"),
        returns="None",
    )

    assert parsed.function_name == "register"
    assert parsed.module_name == "parser_registry"
    assert parsed.decorators == ("staticmethod",)
    assert parsed.arguments == ("self", "registration")
    assert parsed.returns == "None"


def test_decorators_and_arguments_default_to_empty_tuple():
    parsed = ParsedFunction(function_name="f", module_name="m")

    assert parsed.decorators == ()
    assert parsed.arguments == ()


def test_returns_defaults_to_none():
    parsed = ParsedFunction(function_name="f", module_name="m")

    assert parsed.returns is None


def test_immutability():
    parsed = ParsedFunction(function_name="f", module_name="m")

    with pytest.raises(dataclasses.FrozenInstanceError):
        parsed.function_name = "changed"


def test_equality_by_value():
    a = ParsedFunction(function_name="f", module_name="m", arguments=("x",), returns="int")
    b = ParsedFunction(function_name="f", module_name="m", arguments=("x",), returns="int")

    assert a == b


def test_inequality_on_different_returns():
    a = ParsedFunction(function_name="f", module_name="m", returns="int")
    b = ParsedFunction(function_name="f", module_name="m", returns="str")

    assert a != b


def test_hashability():
    a = ParsedFunction(function_name="f", module_name="m", arguments=("x",))
    b = ParsedFunction(function_name="f", module_name="m", arguments=("x",))

    assert hash(a) == hash(b)
    assert len({a, b}) == 1

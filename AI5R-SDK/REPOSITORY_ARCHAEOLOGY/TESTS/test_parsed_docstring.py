"""MWO-RAE-000E -- ParsedDocstring: pure immutable evidence value object."""

import dataclasses

import pytest

from REPOSITORY_ARCHAEOLOGY.evidence.parsed_docstring import ParsedDocstring


def test_construction_holds_all_fields():
    parsed = ParsedDocstring(owner="ParserRegistry", text="Register/unregister/find/list.")

    assert parsed.owner == "ParserRegistry"
    assert parsed.text == "Register/unregister/find/list."


def test_immutability():
    parsed = ParsedDocstring(owner="Module", text="docs")

    with pytest.raises(dataclasses.FrozenInstanceError):
        parsed.text = "changed"


def test_equality_by_value():
    a = ParsedDocstring(owner="Module", text="docs")
    b = ParsedDocstring(owner="Module", text="docs")

    assert a == b


def test_inequality_on_different_owner():
    a = ParsedDocstring(owner="ModuleA", text="docs")
    b = ParsedDocstring(owner="ModuleB", text="docs")

    assert a != b


def test_hashability():
    a = ParsedDocstring(owner="Module", text="docs")
    b = ParsedDocstring(owner="Module", text="docs")

    assert hash(a) == hash(b)
    assert len({a, b}) == 1

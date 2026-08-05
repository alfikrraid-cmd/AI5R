"""MWO-RAE-000E -- ParsedDependency: pure immutable evidence value object."""

import dataclasses

import pytest

from REPOSITORY_ARCHAEOLOGY.evidence.parsed_dependency import ParsedDependency


def test_construction_holds_all_fields():
    parsed = ParsedDependency(source="parser_registry", target="parser_contract", dependency_type="imports")

    assert parsed.source == "parser_registry"
    assert parsed.target == "parser_contract"
    assert parsed.dependency_type == "imports"


def test_immutability():
    parsed = ParsedDependency(source="a", target="b", dependency_type="imports")

    with pytest.raises(dataclasses.FrozenInstanceError):
        parsed.source = "changed"


def test_equality_by_value():
    a = ParsedDependency(source="a", target="b", dependency_type="imports")
    b = ParsedDependency(source="a", target="b", dependency_type="imports")

    assert a == b


def test_inequality_on_different_dependency_type():
    a = ParsedDependency(source="a", target="b", dependency_type="imports")
    b = ParsedDependency(source="a", target="b", dependency_type="inherits")

    assert a != b


def test_hashability():
    a = ParsedDependency(source="a", target="b", dependency_type="imports")
    b = ParsedDependency(source="a", target="b", dependency_type="imports")

    assert hash(a) == hash(b)
    assert len({a, b}) == 1

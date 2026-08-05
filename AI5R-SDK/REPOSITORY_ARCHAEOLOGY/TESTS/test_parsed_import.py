"""MWO-RAE-000E -- ParsedImport: pure immutable evidence value object."""

import dataclasses

import pytest

from REPOSITORY_ARCHAEOLOGY.evidence.parsed_import import ParsedImport


def test_construction_holds_all_fields():
    parsed = ParsedImport(imported_module="pathlib", imported_symbol="Path", alias="P")

    assert parsed.imported_module == "pathlib"
    assert parsed.imported_symbol == "Path"
    assert parsed.alias == "P"


def test_imported_symbol_and_alias_default_to_none():
    parsed = ParsedImport(imported_module="os")

    assert parsed.imported_symbol is None
    assert parsed.alias is None


def test_immutability():
    parsed = ParsedImport(imported_module="os")

    with pytest.raises(dataclasses.FrozenInstanceError):
        parsed.imported_module = "sys"


def test_equality_by_value():
    a = ParsedImport(imported_module="pathlib", imported_symbol="Path")
    b = ParsedImport(imported_module="pathlib", imported_symbol="Path")

    assert a == b


def test_inequality_on_different_alias():
    a = ParsedImport(imported_module="pathlib", imported_symbol="Path", alias="P")
    b = ParsedImport(imported_module="pathlib", imported_symbol="Path", alias=None)

    assert a != b


def test_hashability():
    a = ParsedImport(imported_module="pathlib", imported_symbol="Path")
    b = ParsedImport(imported_module="pathlib", imported_symbol="Path")

    assert hash(a) == hash(b)
    assert len({a, b}) == 1

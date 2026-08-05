"""MWO-RAE-000E -- ParsedComment: pure immutable evidence value object."""

import dataclasses

import pytest

from REPOSITORY_ARCHAEOLOGY.evidence.parsed_comment import ParsedComment


def test_construction_holds_all_fields():
    parsed = ParsedComment(text="# reused, not duplicated", line_number=42)

    assert parsed.text == "# reused, not duplicated"
    assert parsed.line_number == 42


def test_immutability():
    parsed = ParsedComment(text="# note", line_number=1)

    with pytest.raises(dataclasses.FrozenInstanceError):
        parsed.line_number = 2


def test_equality_by_value():
    a = ParsedComment(text="# note", line_number=1)
    b = ParsedComment(text="# note", line_number=1)

    assert a == b


def test_inequality_on_different_line_number():
    a = ParsedComment(text="# note", line_number=1)
    b = ParsedComment(text="# note", line_number=2)

    assert a != b


def test_hashability():
    a = ParsedComment(text="# note", line_number=1)
    b = ParsedComment(text="# note", line_number=1)

    assert hash(a) == hash(b)
    assert len({a, b}) == 1

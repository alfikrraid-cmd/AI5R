"""
MWO-RAE-000D -- ParserRegistration: the immutable value object pairing a
stable name with a ParserContract instance. The registry stores these,
never a bare parser, so every registration has a caller-stable handle
for unregister()/list() without requiring ParserContract itself to carry
identity.
"""

import dataclasses

import pytest

from REPOSITORY_ARCHAEOLOGY.parser_contract import ParserContract
from REPOSITORY_ARCHAEOLOGY.parser_registration import ParserRegistration


class _StubParser(ParserContract):
    def supports(self, path):
        return True

    def parse(self, path):
        return None


def test_parser_registration_holds_name_and_parser():
    parser = _StubParser()
    registration = ParserRegistration(name="stub", parser=parser)

    assert registration.name == "stub"
    assert registration.parser is parser


def test_parser_registration_is_immutable():
    registration = ParserRegistration(name="stub", parser=_StubParser())

    with pytest.raises(dataclasses.FrozenInstanceError):
        registration.name = "changed"


def test_parser_registration_requires_a_name():
    with pytest.raises(ValueError):
        ParserRegistration(name="", parser=_StubParser())


def test_parser_registration_requires_a_parser_contract_instance():
    with pytest.raises(TypeError):
        ParserRegistration(name="stub", parser=object())

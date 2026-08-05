"""
MWO-RAE-000D -- ParserContract: the abstract contract every Repository
Archaeology parser implements. Mirrors ENTERPRISE_DATA_ENGINE's own
Reader(ABC) shape (supports()/read()) -- supports()/parse() here, no
parsing logic of its own.
"""

import pytest

from REPOSITORY_ARCHAEOLOGY.parser_contract import ParserContract


def test_parser_contract_is_abstract():
    with pytest.raises(TypeError):
        ParserContract()


def test_parser_contract_requires_supports_implementation():
    class MissingSupports(ParserContract):
        def parse(self, path):
            return None

    with pytest.raises(TypeError):
        MissingSupports()


def test_parser_contract_requires_parse_implementation():
    class MissingParse(ParserContract):
        def supports(self, path):
            return False

    with pytest.raises(TypeError):
        MissingParse()


def test_concrete_parser_can_implement_both_methods():
    class StubParser(ParserContract):
        def supports(self, path):
            return path.suffix == ".stub"

        def parse(self, path):
            return f"parsed:{path.name}"

    from pathlib import Path

    parser = StubParser()

    assert parser.supports(Path("example.stub")) is True
    assert parser.supports(Path("example.txt")) is False
    assert parser.parse(Path("example.stub")) == "parsed:example.stub"

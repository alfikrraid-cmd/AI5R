"""MWO-RAE-000H -- ParserConfig: pure immutable configuration object."""

import dataclasses
from pathlib import Path

import pytest

from REPOSITORY_ARCHAEOLOGY.config.parser_config import ParserConfig


def test_construction_holds_all_fields():
    config = ParserConfig(enable_python=False, enable_markdown=True, enable_json=False, enable_yaml=True)

    assert config.enable_python is False
    assert config.enable_markdown is True
    assert config.enable_json is False
    assert config.enable_yaml is True


def test_default_values():
    config = ParserConfig()

    assert config.enable_python is True
    assert config.enable_markdown is True
    assert config.enable_json is True
    assert config.enable_yaml is True


def test_immutability():
    config = ParserConfig()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.enable_python = False


def test_equality_by_value():
    a = ParserConfig(enable_python=False)
    b = ParserConfig(enable_python=False)

    assert a == b


def test_inequality_on_different_field():
    a = ParserConfig(enable_yaml=True)
    b = ParserConfig(enable_yaml=False)

    assert a != b


def test_hashability():
    a = ParserConfig()
    b = ParserConfig()

    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_module_has_no_forbidden_imports():
    source = Path(__file__).resolve().parents[1].joinpath("config", "parser_config.py").read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("ParserRegistry", "ParserContract", "evidence", "sqlite3", "SearchEngine", "RepositoryScanner"):
        assert not any(forbidden in line for line in import_lines)

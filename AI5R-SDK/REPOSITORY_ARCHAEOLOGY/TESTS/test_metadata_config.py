"""MWO-RAE-000H -- MetadataConfig: pure immutable configuration object."""

import dataclasses
from pathlib import Path

import pytest

from REPOSITORY_ARCHAEOLOGY.config.metadata_config import MetadataConfig


def test_construction_holds_all_fields():
    config = MetadataConfig(
        include_comments=False,
        include_docstrings=True,
        include_imports=False,
        include_dependencies=True,
    )

    assert config.include_comments is False
    assert config.include_docstrings is True
    assert config.include_imports is False
    assert config.include_dependencies is True


def test_default_values():
    config = MetadataConfig()

    assert config.include_comments is True
    assert config.include_docstrings is True
    assert config.include_imports is True
    assert config.include_dependencies is True


def test_immutability():
    config = MetadataConfig()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.include_comments = False


def test_equality_by_value():
    a = MetadataConfig(include_comments=False)
    b = MetadataConfig(include_comments=False)

    assert a == b


def test_inequality_on_different_field():
    a = MetadataConfig(include_dependencies=True)
    b = MetadataConfig(include_dependencies=False)

    assert a != b


def test_hashability():
    a = MetadataConfig()
    b = MetadataConfig()

    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_module_has_no_forbidden_imports():
    source = Path(__file__).resolve().parents[1].joinpath("config", "metadata_config.py").read_text(encoding="utf-8")
    for forbidden in ("ParserRegistry", "evidence", "sqlite3", "SearchEngine", "RepositoryScanner"):
        assert forbidden not in source

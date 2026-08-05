"""MWO-RAE-000H -- SearchConfig: pure immutable configuration object."""

import dataclasses
from pathlib import Path

import pytest

from REPOSITORY_ARCHAEOLOGY.config.search_config import SearchConfig


def test_construction_holds_all_fields():
    config = SearchConfig(case_sensitive=True, exact_match=True, max_results=50)

    assert config.case_sensitive is True
    assert config.exact_match is True
    assert config.max_results == 50


def test_default_values():
    config = SearchConfig()

    assert config.case_sensitive is False
    assert config.exact_match is False
    assert config.max_results == 100


def test_immutability():
    config = SearchConfig()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.max_results = 10


def test_equality_by_value():
    a = SearchConfig(max_results=25)
    b = SearchConfig(max_results=25)

    assert a == b


def test_inequality_on_different_field():
    a = SearchConfig(case_sensitive=True)
    b = SearchConfig(case_sensitive=False)

    assert a != b


def test_hashability():
    a = SearchConfig(max_results=25)
    b = SearchConfig(max_results=25)

    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_max_results_must_be_positive():
    with pytest.raises(ValueError):
        SearchConfig(max_results=0)


def test_module_has_no_forbidden_imports():
    source = Path(__file__).resolve().parents[1].joinpath("config", "search_config.py").read_text(encoding="utf-8")
    for forbidden in ("ParserRegistry", "evidence", "sqlite3", "SearchEngine", "RepositoryScanner"):
        assert forbidden not in source

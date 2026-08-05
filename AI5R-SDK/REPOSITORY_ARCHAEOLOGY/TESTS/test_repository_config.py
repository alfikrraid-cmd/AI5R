"""
MWO-RAE-000H -- RepositoryConfig: the single, canonical top-level
configuration object composing ScannerConfig/ParserConfig/
MetadataConfig/SearchConfig. Pure immutable value object -- no loading
logic, no env var reading.
"""

import dataclasses
from pathlib import Path

import pytest

from REPOSITORY_ARCHAEOLOGY.config.metadata_config import MetadataConfig
from REPOSITORY_ARCHAEOLOGY.config.parser_config import ParserConfig
from REPOSITORY_ARCHAEOLOGY.config.repository_config import RepositoryConfig
from REPOSITORY_ARCHAEOLOGY.config.scanner_config import ScannerConfig
from REPOSITORY_ARCHAEOLOGY.config.search_config import SearchConfig


def test_default_values_compose_each_sub_config_defaults():
    config = RepositoryConfig()

    assert config.scanner_config == ScannerConfig()
    assert config.parser_config == ParserConfig()
    assert config.metadata_config == MetadataConfig()
    assert config.search_config == SearchConfig()


def test_construction_holds_explicit_sub_configs():
    scanner = ScannerConfig(recursive_scan=False)
    config = RepositoryConfig(scanner_config=scanner)

    assert config.scanner_config is scanner


def test_immutability():
    config = RepositoryConfig()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.scanner_config = ScannerConfig()


def test_equality_by_value():
    a = RepositoryConfig(parser_config=ParserConfig(enable_python=False))
    b = RepositoryConfig(parser_config=ParserConfig(enable_python=False))

    assert a == b


def test_inequality_on_different_sub_config():
    a = RepositoryConfig(search_config=SearchConfig(max_results=10))
    b = RepositoryConfig(search_config=SearchConfig(max_results=20))

    assert a != b


def test_hashability():
    a = RepositoryConfig()
    b = RepositoryConfig()

    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_module_has_no_forbidden_imports_beyond_the_four_sub_configs():
    source = Path(__file__).resolve().parents[1].joinpath("config", "repository_config.py").read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("ParserRegistry", "ParserContract", "evidence", "sqlite3", "SearchEngine", "RepositoryScanner"):
        assert not any(forbidden in line for line in import_lines)

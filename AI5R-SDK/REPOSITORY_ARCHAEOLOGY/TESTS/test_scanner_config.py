"""MWO-RAE-000H -- ScannerConfig: pure immutable configuration object."""

import dataclasses
from pathlib import Path

import pytest

from REPOSITORY_ARCHAEOLOGY.config.scanner_config import ScannerConfig


def test_construction_holds_all_fields():
    config = ScannerConfig(
        supported_extensions=(".py", ".md"),
        ignored_directories=(".git", "__pycache__"),
        follow_symlinks=True,
        recursive_scan=False,
    )

    assert config.supported_extensions == (".py", ".md")
    assert config.ignored_directories == (".git", "__pycache__")
    assert config.follow_symlinks is True
    assert config.recursive_scan is False


def test_default_values():
    config = ScannerConfig()

    assert config.supported_extensions == ()
    assert config.ignored_directories == ()
    assert config.follow_symlinks is False
    assert config.recursive_scan is True


def test_immutability():
    config = ScannerConfig()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.recursive_scan = False


def test_equality_by_value():
    a = ScannerConfig(supported_extensions=(".py",))
    b = ScannerConfig(supported_extensions=(".py",))

    assert a == b


def test_inequality_on_different_field():
    a = ScannerConfig(follow_symlinks=True)
    b = ScannerConfig(follow_symlinks=False)

    assert a != b


def test_hashability():
    a = ScannerConfig(supported_extensions=(".py", ".md"))
    b = ScannerConfig(supported_extensions=(".py", ".md"))

    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_module_has_no_forbidden_imports():
    source = Path(__file__).resolve().parents[1].joinpath("config", "scanner_config.py").read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("RepositoryScanner", "ParserRegistry", "evidence", "sqlite3", "SearchEngine"):
        assert not any(forbidden in line for line in import_lines)

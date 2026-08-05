"""
MWO-RAE-000H -- verifies the config package's barrel exports exactly
the five canonical configuration objects, and that the whole config
package remains dependency-free from RepositoryScanner/ParserRegistry/
evidence/SQLite/Search Engine (import correctness).
"""

import importlib
import pkgutil
from pathlib import Path

from REPOSITORY_ARCHAEOLOGY import config


def test_exports_all_five_config_objects():
    expected = {
        "RepositoryConfig",
        "ScannerConfig",
        "ParserConfig",
        "MetadataConfig",
        "SearchConfig",
    }

    for name in expected:
        assert hasattr(config, name), f"config package does not export {name}"


def test_exports_nothing_beyond_the_five_canonical_objects():
    expected = {
        "RepositoryConfig",
        "ScannerConfig",
        "ParserConfig",
        "MetadataConfig",
        "SearchConfig",
    }

    assert set(config.__all__) == expected


def test_every_config_module_imports_cleanly_and_independently():
    # Import correctness: each module in config/ must import on its own,
    # with no circular dependency on the rest of the package.
    for module_info in pkgutil.iter_modules(config.__path__):
        importlib.import_module(f"REPOSITORY_ARCHAEOLOGY.config.{module_info.name}")


def test_config_package_does_not_import_repository_scanner_or_parser_registry():
    source = Path(config.__file__).read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("RepositoryScanner", "ParserRegistry", "SearchEngine", "MetadataExtractor", "sqlite3"):
        assert not any(forbidden in line for line in import_lines)

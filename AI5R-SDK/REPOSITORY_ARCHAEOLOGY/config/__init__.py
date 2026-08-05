"""
MWO-RAE-000H -- canonical Repository Archaeology configuration package.
The single configuration source for RepositoryScanner, FileHashService,
ParserRegistry, future parsers, MetadataExtractor, the SQLite
repository, and Repository Search -- none of which is implemented or
imported here. Pure, dependency-free configuration objects only.
"""

from .metadata_config import MetadataConfig
from .parser_config import ParserConfig
from .repository_config import RepositoryConfig
from .scanner_config import ScannerConfig
from .search_config import SearchConfig

__all__ = [
    "MetadataConfig",
    "ParserConfig",
    "RepositoryConfig",
    "ScannerConfig",
    "SearchConfig",
]

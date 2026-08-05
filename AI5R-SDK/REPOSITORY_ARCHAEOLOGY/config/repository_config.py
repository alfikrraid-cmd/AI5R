"""
MWO-RAE-000H -- RepositoryConfig: the single, canonical top-level
configuration object for the Repository Archaeology Engine. Composes
ScannerConfig/ParserConfig/MetadataConfig/SearchConfig -- the only four
sub-configurations this MWO gave an explicit field list for. No
FileHashService-specific fields were added: the mission named
FileHashService as a future consumer of this centralized config point,
but gave no field list for it, so none was invented here (disclosed in
the Repository Archaeology Report, not silently added).

Pure data: no loading logic, no environment variable reading, and no
dependency on RepositoryScanner, ParserRegistry, evidence objects,
SQLite, or the search engine themselves -- only on the other
configuration objects in this same package.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .metadata_config import MetadataConfig
from .parser_config import ParserConfig
from .scanner_config import ScannerConfig
from .search_config import SearchConfig


@dataclass(frozen=True, slots=True)
class RepositoryConfig:
    scanner_config: ScannerConfig = field(default_factory=ScannerConfig)
    parser_config: ParserConfig = field(default_factory=ParserConfig)
    metadata_config: MetadataConfig = field(default_factory=MetadataConfig)
    search_config: SearchConfig = field(default_factory=SearchConfig)


__all__ = ["RepositoryConfig"]

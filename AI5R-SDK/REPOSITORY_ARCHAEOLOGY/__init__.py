"""REPOSITORY_ARCHAEOLOGY -- canonical exception hierarchy for AI5R Repository
Archaeology components.

Every Repository Archaeology component (RepositoryScanner, FileHashService,
ParserRegistry, Parser implementations, MetadataExtractor, the SQLite
Repository, and the Search Engine) must raise exceptions from this
hierarchy. This package currently defines the exception hierarchy only;
no scanner, parser, metadata, or search implementation lives here.
"""

from REPOSITORY_ARCHAEOLOGY.repository_exception import RepositoryException
from REPOSITORY_ARCHAEOLOGY.scanner_exception import (
    InvalidRepositoryError,
    RepositoryAccessDeniedError,
    RepositoryNotFoundError,
    ScanCancelledError,
)
from REPOSITORY_ARCHAEOLOGY.parser_exception import (
    InvalidParserRegistrationError,
    ParserException,
    ParserNotFoundError,
    UnsupportedExtensionError,
    UnsupportedLanguageError,
)
from REPOSITORY_ARCHAEOLOGY.metadata_exception import (
    InvalidMetadataError,
    MetadataException,
    MetadataExtractionError,
)
from REPOSITORY_ARCHAEOLOGY.search_exception import (
    EvidenceNotFoundError,
    RepositoryIndexCorruptedError,
    SearchException,
)

__all__ = [
    "RepositoryException",
    "RepositoryNotFoundError",
    "InvalidRepositoryError",
    "RepositoryAccessDeniedError",
    "ScanCancelledError",
    "ParserException",
    "ParserNotFoundError",
    "UnsupportedLanguageError",
    "UnsupportedExtensionError",
    "InvalidParserRegistrationError",
    "MetadataException",
    "MetadataExtractionError",
    "InvalidMetadataError",
    "SearchException",
    "EvidenceNotFoundError",
    "RepositoryIndexCorruptedError",
]

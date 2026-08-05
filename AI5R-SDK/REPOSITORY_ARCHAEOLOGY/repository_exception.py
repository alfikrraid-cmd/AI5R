"""Repository Archaeology exception hierarchy -- base exception.

Canonical base class for every exception raised by any Repository
Archaeology component (RepositoryScanner, FileHashService, ParserRegistry,
Parser implementations, MetadataExtractor, the SQLite Repository, and the
Search Engine). No implementation logic lives in this module -- it defines
the exception hierarchy only.
"""

from __future__ import annotations


class RepositoryException(Exception):
    """Base class for every error raised by a Repository Archaeology component."""

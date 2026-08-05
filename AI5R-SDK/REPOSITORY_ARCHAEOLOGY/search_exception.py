"""Repository Archaeology exception hierarchy -- search exceptions.

Raised by the Search Engine. The Search Engine itself is out of scope for
this module; only the exceptions it must raise are defined here.
"""

from __future__ import annotations

from REPOSITORY_ARCHAEOLOGY.repository_exception import RepositoryException


class SearchException(RepositoryException):
    """Base class for every search-related error."""


class EvidenceNotFoundError(SearchException):
    """Raised when no evidence matches the requested search query."""


class RepositoryIndexCorruptedError(SearchException):
    """Raised when the repository search index fails integrity validation."""

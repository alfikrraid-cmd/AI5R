"""Repository Archaeology exception hierarchy -- metadata exceptions.

Raised by MetadataExtractor. MetadataExtractor itself is out of scope for
this module; only the exceptions it must raise are defined here.
"""

from __future__ import annotations

from REPOSITORY_ARCHAEOLOGY.repository_exception import RepositoryException


class MetadataException(RepositoryException):
    """Base class for every metadata-extraction-related error."""


class MetadataExtractionError(MetadataException):
    """Raised when metadata extraction from a repository artifact fails."""


class InvalidMetadataError(MetadataException):
    """Raised when extracted metadata fails validation."""

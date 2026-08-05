"""Repository Archaeology exception hierarchy -- scanner exceptions.

Raised by RepositoryScanner. RepositoryScanner itself is out of scope for
this module; only the exceptions it must raise are defined here. Each
scanner exception inherits directly from RepositoryException -- there is
no intermediate ScannerException base.
"""

from __future__ import annotations

from REPOSITORY_ARCHAEOLOGY.repository_exception import RepositoryException


class RepositoryNotFoundError(RepositoryException):
    """Raised when the target repository path does not exist."""


class InvalidRepositoryError(RepositoryException):
    """Raised when the target path exists but is not a valid repository."""


class RepositoryAccessDeniedError(RepositoryException):
    """Raised when the target repository cannot be accessed due to permissions."""


class ScanCancelledError(RepositoryException):
    """Raised when a repository scan is cancelled before completion."""

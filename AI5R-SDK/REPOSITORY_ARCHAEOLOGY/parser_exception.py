"""Repository Archaeology exception hierarchy -- parser exceptions.

Raised by ParserRegistry and future Parser implementations. Neither
ParserRegistry nor any Parser implementation is in scope for this module;
only the exceptions they must raise are defined here.
"""

from __future__ import annotations

from REPOSITORY_ARCHAEOLOGY.repository_exception import RepositoryException


class ParserException(RepositoryException):
    """Base class for every parser-related error."""


class ParserNotFoundError(ParserException):
    """Raised when no parser is registered for the requested identifier."""


class UnsupportedLanguageError(ParserException):
    """Raised when a parser is requested for a language it does not support."""


class UnsupportedExtensionError(ParserException):
    """Raised when no registered parser supports the given file extension."""


class InvalidParserRegistrationError(ParserException):
    """Raised when a parser fails to meet the requirements for registration."""

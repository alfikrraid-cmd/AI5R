import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

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

SCANNER_EXCEPTIONS = (
    RepositoryNotFoundError,
    InvalidRepositoryError,
    RepositoryAccessDeniedError,
    ScanCancelledError,
)

PARSER_EXCEPTIONS = (
    ParserNotFoundError,
    UnsupportedLanguageError,
    UnsupportedExtensionError,
    InvalidParserRegistrationError,
)

METADATA_EXCEPTIONS = (
    MetadataExtractionError,
    InvalidMetadataError,
)

SEARCH_EXCEPTIONS = (
    EvidenceNotFoundError,
    RepositoryIndexCorruptedError,
)

ALL_LEAF_EXCEPTIONS = SCANNER_EXCEPTIONS + PARSER_EXCEPTIONS + METADATA_EXCEPTIONS + SEARCH_EXCEPTIONS
ALL_GROUP_BASES = (ParserException, MetadataException, SearchException)


def test_repository_exception_inherits_exception():
    assert issubclass(RepositoryException, Exception)


def test_group_bases_inherit_repository_exception():
    for cls in ALL_GROUP_BASES:
        assert issubclass(cls, RepositoryException)


def test_scanner_exceptions_inherit_repository_exception_directly():
    for cls in SCANNER_EXCEPTIONS:
        assert issubclass(cls, RepositoryException)
        assert RepositoryException in cls.__bases__


def test_parser_exceptions_inherit_parser_exception():
    for cls in PARSER_EXCEPTIONS:
        assert issubclass(cls, ParserException)
        assert issubclass(cls, RepositoryException)


def test_metadata_exceptions_inherit_metadata_exception():
    for cls in METADATA_EXCEPTIONS:
        assert issubclass(cls, MetadataException)
        assert issubclass(cls, RepositoryException)


def test_search_exceptions_inherit_search_exception():
    for cls in SEARCH_EXCEPTIONS:
        assert issubclass(cls, SearchException)
        assert issubclass(cls, RepositoryException)


def test_every_leaf_exception_is_a_repository_exception_instance():
    for cls in ALL_LEAF_EXCEPTIONS:
        instance = cls("boom")
        assert isinstance(instance, RepositoryException)
        assert isinstance(instance, Exception)


def test_message_is_preserved_for_every_leaf_exception():
    for cls in ALL_LEAF_EXCEPTIONS:
        instance = cls("something went wrong")
        assert str(instance) == "something went wrong"


def test_exception_chaining_preserves_cause():
    original = ValueError("root cause")

    try:
        try:
            raise original
        except ValueError as exc:
            raise RepositoryNotFoundError("repository missing") from exc
    except RepositoryNotFoundError as chained:
        assert chained.__cause__ is original
        assert str(chained) == "repository missing"


def test_catching_base_repository_exception_catches_every_leaf():
    for cls in ALL_LEAF_EXCEPTIONS:
        with pytest.raises(RepositoryException):
            raise cls("boom")


def test_catching_group_base_does_not_catch_sibling_group():
    with pytest.raises(ParserException):
        try:
            raise MetadataExtractionError("metadata failure")
        except ParserException:
            pytest.fail("MetadataExtractionError must not be caught as ParserException")
        except MetadataException:
            raise ParserException("re-raised for assertion symmetry") from None


def test_repository_exception_is_importable_from_its_own_module():
    from REPOSITORY_ARCHAEOLOGY import repository_exception

    assert repository_exception.RepositoryException is RepositoryException


def test_no_leaf_exception_class_defines_extra_public_methods():
    interpreter_injected = {
        "__module__",
        "__qualname__",
        "__doc__",
        "__firstlineno__",
        "__static_attributes__",
        "__dict__",
        "__weakref__",
    }
    for cls in ALL_LEAF_EXCEPTIONS + ALL_GROUP_BASES + (RepositoryException,):
        own_members = set(vars(cls).keys()) - interpreter_injected
        assert not own_members, f"{cls.__name__} defines implementation logic: {own_members}"

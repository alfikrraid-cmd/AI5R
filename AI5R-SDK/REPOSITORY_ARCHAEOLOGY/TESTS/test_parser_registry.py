"""
MWO-RAE-000D -- ParserRegistry: register/unregister/find/list over
ParserRegistration entries. Mirrors SKILL_LOADER.skill_registry's exact
method names and duplicate-rejection discipline
(register/unregister/find/list, ValueError on duplicate register,
KeyError on missing unregister) -- no second registry pattern is
introduced. find() is predicate-based (first registered parser whose
supports(path) is True), matching this registry's specific job: locate
the correct parser for a given file, not look a parser up by name.

The registry itself never parses anything -- every test constructs a
stub ParserContract; parse() bodies are never asserted on here.
"""

from pathlib import Path

import pytest

from REPOSITORY_ARCHAEOLOGY.parser_contract import ParserContract
from REPOSITORY_ARCHAEOLOGY.parser_registration import ParserRegistration
from REPOSITORY_ARCHAEOLOGY.parser_registry import ParserRegistry


class _SuffixParser(ParserContract):
    """Stub: supports() by file suffix only. No parsing logic."""

    def __init__(self, suffix):
        self._suffix = suffix

    def supports(self, path):
        return path.suffix == self._suffix

    def parse(self, path):
        return f"parsed:{path.name}"


def _registration(name, suffix):
    return ParserRegistration(name=name, parser=_SuffixParser(suffix))


# -- registration --------------------------------------------------------


def test_register_adds_a_parser_registration():
    registry = ParserRegistry()
    registration = _registration("python", ".py")

    registry.register(registration)

    assert registry.list() == (registration,)


def test_register_returns_none():
    registry = ParserRegistry()

    result = registry.register(_registration("python", ".py"))

    assert result is None


def test_register_rejects_non_parser_registration_input():
    registry = ParserRegistry()

    with pytest.raises(TypeError):
        registry.register(_SuffixParser(".py"))


# -- duplicate registration rejection -------------------------------------


def test_register_rejects_duplicate_name():
    registry = ParserRegistry()
    registry.register(_registration("python", ".py"))

    with pytest.raises(ValueError):
        registry.register(_registration("python", ".pyc"))


def test_duplicate_rejection_leaves_the_original_registration_intact():
    registry = ParserRegistry()
    original = _registration("python", ".py")
    registry.register(original)

    try:
        registry.register(_registration("python", ".pyc"))
    except ValueError:
        pass

    assert registry.list() == (original,)


# -- unregister -------------------------------------------------------------


def test_unregister_removes_a_registered_parser():
    registry = ParserRegistry()
    registry.register(_registration("python", ".py"))

    registry.unregister("python")

    assert registry.list() == ()


def test_unregister_unknown_name_raises_key_error():
    registry = ParserRegistry()

    with pytest.raises(KeyError):
        registry.unregister("does-not-exist")


def test_unregister_then_reregister_the_same_name_succeeds():
    registry = ParserRegistry()
    registry.register(_registration("python", ".py"))
    registry.unregister("python")

    registry.register(_registration("python", ".pyc"))

    assert registry.list()[0].name == "python"


# -- lookup (find) ------------------------------------------------------------


def test_find_returns_the_supporting_parser():
    registry = ParserRegistry()
    python_registration = _registration("python", ".py")
    registry.register(python_registration)

    found = registry.find(Path("module.py"))

    assert found is python_registration.parser


def test_find_returns_none_when_registry_is_empty():
    registry = ParserRegistry()

    assert registry.find(Path("module.py")) is None


# -- unsupported file ---------------------------------------------------------


def test_find_returns_none_for_unsupported_file_type():
    registry = ParserRegistry()
    registry.register(_registration("python", ".py"))

    assert registry.find(Path("notes.md")) is None


def test_find_does_not_raise_for_unsupported_file_type():
    registry = ParserRegistry()
    registry.register(_registration("python", ".py"))

    # Must return None, never raise -- the registry only looks up, it
    # never parses or judges the file as an error condition.
    result = registry.find(Path("image.png"))

    assert result is None


# -- multiple parser registration ---------------------------------------------


def test_multiple_parsers_can_be_registered_simultaneously():
    registry = ParserRegistry()
    registry.register(_registration("python", ".py"))
    registry.register(_registration("markdown", ".md"))
    registry.register(_registration("json", ".json"))

    assert len(registry.list()) == 3


def test_find_selects_the_correct_parser_among_several():
    registry = ParserRegistry()
    python_registration = _registration("python", ".py")
    markdown_registration = _registration("markdown", ".md")
    registry.register(python_registration)
    registry.register(markdown_registration)

    assert registry.find(Path("README.md")) is markdown_registration.parser
    assert registry.find(Path("main.py")) is python_registration.parser


def test_find_returns_the_first_registered_match_when_multiple_could_support(): # noqa: E501
    registry = ParserRegistry()

    class _AlwaysSupports(ParserContract):
        def supports(self, path):
            return True

        def parse(self, path):
            return None

    first = ParserRegistration(name="first", parser=_AlwaysSupports())
    second = ParserRegistration(name="second", parser=_AlwaysSupports())
    registry.register(first)
    registry.register(second)

    assert registry.find(Path("anything.ext")) is first.parser


# -- list ----------------------------------------------------------------------


def test_list_returns_an_immutable_snapshot():
    registry = ParserRegistry()
    registry.register(_registration("python", ".py"))

    snapshot = registry.list()

    assert isinstance(snapshot, tuple)


def test_list_is_empty_for_a_freshly_constructed_registry():
    registry = ParserRegistry()

    assert registry.list() == ()


def test_mutating_the_returned_list_snapshot_does_not_affect_the_registry():
    registry = ParserRegistry()
    registry.register(_registration("python", ".py"))

    snapshot = registry.list()
    # tuples have no append; this test documents that list() cannot be
    # used to mutate the registry's internal state, by construction.
    assert not hasattr(snapshot, "append")


# -- dependency injection / no global mutable state ----------------------------


def test_two_registry_instances_do_not_share_state():
    registry_a = ParserRegistry()
    registry_b = ParserRegistry()

    registry_a.register(_registration("python", ".py"))

    assert registry_b.list() == ()


def test_registry_requires_no_constructor_arguments_but_accepts_injection_point():
    # Dependency-injection friendly: constructible with zero args (for
    # simple composition), and registration is done via an explicit
    # method call, never via module-level global state.
    registry = ParserRegistry()

    assert registry.list() == ()

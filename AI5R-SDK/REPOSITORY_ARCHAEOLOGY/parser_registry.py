"""
MWO-RAE-000D -- ParserRegistry: the single canonical store of registered
Repository Archaeology parsers. No persistence, no parsing, no file I/O
of its own -- pure register/unregister/find/list over ParserRegistration
records, mirroring SKILL_LOADER.skill_registry.SkillRegistry's exact
method names and duplicate-rejection discipline
(ValueError on duplicate register, KeyError on missing unregister). No
second registry implementation is introduced anywhere in this package.

find() is predicate-based, not name-based: it returns the first
registered parser whose supports(path) is True, matching this registry's
specific job -- locate the correct parser for a given file -- as
distinct from SkillRegistry's find-by-id lookup. Registration order is
preserved (Python dict insertion order), so registration order is the
tie-break when more than one parser could support the same file.

Dependency-injection friendly: no module-level singleton, no global
mutable state. Each ParserRegistry instance owns its own state; callers
construct one and pass it explicitly to whatever needs parser lookup.
"""

from __future__ import annotations

from pathlib import Path

from .parser_contract import ParserContract
from .parser_registration import ParserRegistration


class ParserRegistry:
    """Register/unregister/find/list over ParserRegistration entries."""

    def __init__(self) -> None:
        self._registrations: dict[str, ParserRegistration] = {}

    def register(self, registration: ParserRegistration) -> None:
        if not isinstance(registration, ParserRegistration):
            raise TypeError("registration must be a ParserRegistration")

        if registration.name in self._registrations:
            raise ValueError(f"Parser already registered: {registration.name}")

        self._registrations[registration.name] = registration

    def unregister(self, name: str) -> None:
        if name not in self._registrations:
            raise KeyError(f"Parser not registered: {name}")

        del self._registrations[name]

    def find(self, path: Path) -> ParserContract | None:
        for registration in self._registrations.values():
            if registration.parser.supports(path):
                return registration.parser

        return None

    def list(self) -> tuple[ParserRegistration, ...]:
        return tuple(self._registrations.values())


__all__ = ["ParserRegistry"]

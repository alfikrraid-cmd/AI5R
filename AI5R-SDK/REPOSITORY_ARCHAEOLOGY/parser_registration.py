"""
MWO-RAE-000D -- ParserRegistration: the immutable value object pairing a
stable name with a ParserContract instance. ParserRegistry stores these,
never a bare parser, so every registration has a caller-stable handle
for unregister()/list() without requiring ParserContract itself to carry
identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parser_contract import ParserContract


@dataclass(frozen=True, slots=True)
class ParserRegistration:
    """Immutable: a registered parser, named. Never mutated after construction."""

    name: str
    parser: ParserContract

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name is required")
        if not isinstance(self.parser, ParserContract):
            raise TypeError("parser must implement ParserContract")


__all__ = ["ParserRegistration"]

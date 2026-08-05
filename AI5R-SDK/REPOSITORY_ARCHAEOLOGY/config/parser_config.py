"""
MWO-RAE-000H -- ParserConfig: canonical, immutable configuration
toggling which parser types are enabled. Does not import ParserRegistry
or ParserContract -- a config object only ever describes intent, it
never wires or constructs the systems it configures.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParserConfig:
    enable_python: bool = True
    enable_markdown: bool = True
    enable_json: bool = True
    enable_yaml: bool = True


__all__ = ["ParserConfig"]

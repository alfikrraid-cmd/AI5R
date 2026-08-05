"""
MWO-RAE-000E -- ParsedComment: canonical Repository Evidence Object
representing one parsed inline/standalone comment. Pure immutable
value object.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedComment:
    text: str
    line_number: int


__all__ = ["ParsedComment"]

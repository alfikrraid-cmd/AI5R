"""
MWO-RAE-000E -- ParsedDocstring: canonical Repository Evidence Object
representing one parsed docstring. `owner` names the module/class/
function the docstring belongs to. Pure immutable value object.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedDocstring:
    owner: str
    text: str


__all__ = ["ParsedDocstring"]

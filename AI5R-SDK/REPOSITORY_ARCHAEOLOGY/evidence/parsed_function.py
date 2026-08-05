"""
MWO-RAE-000E -- ParsedFunction: canonical Repository Evidence Object
representing one parsed function/method definition. Pure immutable
value object. decorators/arguments are tuples, not lists -- required
for hashability.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedFunction:
    function_name: str
    module_name: str
    decorators: tuple[str, ...] = ()
    arguments: tuple[str, ...] = ()
    returns: str | None = None


__all__ = ["ParsedFunction"]

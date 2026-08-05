"""
MWO-RAE-000E -- ParsedClass: canonical Repository Evidence Object
representing one parsed class definition. Pure immutable value object.
base_classes/decorators are tuples, not lists -- required for the
frozen dataclass to remain hashable (see TESTS/test_parsed_class.py).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedClass:
    class_name: str
    module_name: str
    base_classes: tuple[str, ...] = ()
    decorators: tuple[str, ...] = ()


__all__ = ["ParsedClass"]

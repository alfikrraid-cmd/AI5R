"""
MWO-RAE-000E -- ParsedDependency: canonical Repository Evidence Object
representing one parsed relationship between two artifacts (e.g. an
import, an inheritance edge). Pure immutable value object.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedDependency:
    source: str
    target: str
    dependency_type: str


__all__ = ["ParsedDependency"]

"""
MWO-RAE-000E -- ParsedModule: canonical Repository Evidence Object
representing one parsed source file. Pure immutable value object: no
parser logic, no dict, no serialization. Mirrors FOUNDATION.file_hash_
service.FileHashResult's exact style (plain frozen dataclass, typed
fields, no methods) rather than FOUNDATION.canonical_object.
CanonicalObject/ENGINEERING_MEMORY.parsed_engineering_document.
ParsedEngineeringDocument, both of which are mutable, dict-bearing, and
serialization-oriented -- incompatible with this MWO's explicit "no
dict, no JSON, no serialization" requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ParsedModule:
    module_name: str
    file_path: Path
    language: str


__all__ = ["ParsedModule"]

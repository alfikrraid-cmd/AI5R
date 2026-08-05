"""
MWO-RAE-000E -- ParsedImport: canonical Repository Evidence Object
representing one parsed import statement. Pure immutable value object.
imported_symbol is None for a plain `import module` statement; alias is
None when no `as` clause is present.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedImport:
    imported_module: str
    imported_symbol: str | None = None
    alias: str | None = None


__all__ = ["ParsedImport"]

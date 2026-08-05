"""
MWO-RAE-000H -- MetadataConfig: canonical, immutable configuration for
MetadataExtractor (not implemented by this MWO). Pure data, no
extraction logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetadataConfig:
    include_comments: bool = True
    include_docstrings: bool = True
    include_imports: bool = True
    include_dependencies: bool = True


__all__ = ["MetadataConfig"]

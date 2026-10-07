"""Drawing Reference Normalizer and Component Parser.

Provides canonical normalization of mechanical seal and pump drawing references
while strictly preserving the original raw reference in evidence and linkage models.
"""

from __future__ import annotations

import re

_COMPOUND_SPLIT_PATTERN = re.compile(r"\s*(?:/|,|&|\bAND\b)\s*", re.IGNORECASE)
_WHITESPACE_UNDERSCORE_PATTERN = re.compile(r"[\s_]+")
_CONSECUTIVE_HYPHENS = re.compile(r"-+")
_SAFE_PATH_PATTERN = re.compile(r"[^A-Za-z0-9_-]")


def normalize_reference(raw: str | None) -> str:
    """Normalizes a single drawing reference token.

    Rules:
    - Strips leading and trailing whitespace.
    - Converts to uppercase.
    - Replaces whitespace and underscores with a hyphen.
    - Collapses consecutive hyphens.
    - Strips leading and trailing hyphens.

    Examples:
        'TMI_8B_1525' -> 'TMI-8B-1525'
        'GA_243047' -> 'GA-243047'
        '  e12894  ' -> 'E12894'
    """
    if not raw:
        return ""
    text = raw.strip().upper()
    text = _WHITESPACE_UNDERSCORE_PATTERN.sub("-", text)
    text = _CONSECUTIVE_HYPHENS.sub("-", text)
    return text.strip("-")


def parse_reference_components(raw: str | None) -> list[str]:
    """Splits compound drawing references into discrete normalized tokens.

    Compound references often combine multiple drawings (e.g. pump GA + seal drawing):
        'E13407/GA-187530' -> ['E13407', 'GA-187530']
        'GA-230821/GA-230826' -> ['GA-230821', 'GA-230826']
        'TMI_8B_1525' -> ['TMI-8B-1525']
    """
    if not raw:
        return []
    parts = _COMPOUND_SPLIT_PATTERN.split(raw.strip())
    results: list[str] = []
    for part in parts:
        norm = normalize_reference(part)
        if norm and norm not in results:
            results.append(norm)
    return results


def sanitize_for_path_segment(token: str | None, default: str = "UNKNOWN") -> str:
    """Sanitizes an identity string to safely form part of an object storage key.

    Strictly removes all path traversal characters (slashes, dots, null bytes).
    Guarantees no '../' or '/' segment injection.
    """
    norm = normalize_reference(token) if token else ""
    safe = _SAFE_PATH_PATTERN.sub("", norm)
    return safe[:64] if safe else default


__all__ = [
    "normalize_reference",
    "parse_reference_components",
    "sanitize_for_path_segment",
]


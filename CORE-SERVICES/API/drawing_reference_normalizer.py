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


# ==============================================================================
# AUTHORITATIVE BUSINESS RULES: R9D-BR01, R9D-BR02 & R9D-BR03
# ==============================================================================
# R9D-BR01: FOLDER_SCOPE_EXPANSION
# The top-level archive folder identifies equipment scope for every drawing physically
# contained in that folder. Grouped unit suffixes expand:
#   AB  -> tag A + tag B (e.g. 101-P-2 AB New -> 101-P-2A, 101-P-2B)
#   ABC -> tag A + tag B + tag C (e.g. 920-P-2 ABC New -> 920-P-2A, 920-P-2B, 920-P-2C)
# Critical domain boundary: Equipment unit suffix (A/B/C) and seal side (DE/NDE) are
# strictly independent dimensions. Never map A->DE or B->NDE.
# One physical drawing binary is linked to multiple pumps (zero binary duplication).
#
# R9D-BR02: DRAWING_SIDE_ASSOCIATION
# Explicit DE -> 'DE'; explicit NDE -> 'NDE'; explicit SINGLE -> 'SINGLE';
# explicit equipment-wide / side-independent -> 'NA'.
# When no reliable side evidence exists -> equipment_side=None (SQL NULL).
# NULL means SIDE_NOT_YET_CLASSIFIED. Never default to 'UNKNOWN'.
#
# R9D-BR03: DRAWING_GENERATION_LINEAGE
# E-series drawings (e.g., E12930) represent the older / legacy drawing generation.
# GA-series drawings generally represent the newer drawing generation.
# IMPORTANT:
# - E-series is classified as 'LEGACY' when applicable.
# - GA-series is classified as 'NEWER' when applicable.
# - DO NOT automatically create E -> superseded_by -> GA without validated engineering
#   evidence (same equipment archive/folder, drawing reference data/title block,
#   engineering records, approved mapping, or explicit system-owner confirmation).
# - NEVER delete E-series records when a GA drawing exists.
# - Preserves both identities and their historical references.
# - Without validated successor:
#     E drawing: generation='LEGACY', superseded_by=None
#     GA drawing: generation='NEWER', supersedes=None
# ==============================================================================

ALLOWED_EQUIPMENT_SIDES: frozenset[str] = frozenset({"DE", "NDE", "SINGLE", "NA"})

_E_SERIES_PATTERN = re.compile(r"^E[-_]?\d+", re.IGNORECASE)
_GA_SERIES_PATTERN = re.compile(r"^GA[-_]?\d+", re.IGNORECASE)


def validate_equipment_side(side: str | None) -> str | None:
    """Validates and normalizes mechanical seal equipment side attribute (R9D-BR02).

    Allowed non-null values: 'DE', 'NDE', 'SINGLE', 'NA'.
    Returns None (SQL NULL) when no side evidence exists (SIDE_NOT_YET_CLASSIFIED).
    Never defaults to 'UNKNOWN'.

    Raises:
        ValueError: If side is not recognized among allowed values.
    """
    if side is None:
        return None
    cleaned = str(side).strip().upper()
    if not cleaned:
        return None
    if cleaned not in ALLOWED_EQUIPMENT_SIDES:
        raise ValueError(
            f"Invalid equipment_side '{side}'. Allowed values are: "
            f"{', '.join(sorted(ALLOWED_EQUIPMENT_SIDES))} or None."
        )
    return cleaned


def classify_drawing_generation(drawing_number: str | None) -> str | None:
    """Classifies drawing generation convention (R9D-BR03).

    Returns:
        'LEGACY' for E-series drawings (e.g. E12930, E12894).
        'NEWER' for GA-series drawings (e.g. GA-243047, GA289674).
        None for other standard or unclassified drawing series.

    Note: This is a classification convention only; it does NOT establish
    an automatic superseding relationship.
    """
    if not drawing_number:
        return None
    cleaned = drawing_number.strip().upper()
    if _E_SERIES_PATTERN.match(cleaned):
        return "LEGACY"
    if _GA_SERIES_PATTERN.match(cleaned):
        return "NEWER"
    return None


__all__ = [
    "ALLOWED_EQUIPMENT_SIDES",
    "classify_drawing_generation",
    "normalize_reference",
    "parse_reference_components",
    "sanitize_for_path_segment",
    "validate_equipment_side",
]

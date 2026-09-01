"""Canonical extraction and spelling normalization for LTSA equipment tags."""

from __future__ import annotations

import re


# An equipment tag is an area number, P, equipment number, and optional
# one- or two-letter suffix. Separators are presentation only; validation of
# whether the exact canonical tag exists remains the caller's responsibility.
EQUIPMENT_TAG_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?P<area>\d{3})[\s-]*P[\s-]*(?P<number>\d+)[\s-]*(?P<suffix>AR|BR|[A-Za-z])?(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def normalize_equipment_tag_match(match: re.Match[str]) -> str:
    canonical = f"{match.group('area')}-P-{match.group('number')}"
    suffix = match.group('suffix')
    return canonical + (suffix.upper() if suffix else "")


def normalize_equipment_tag_text(text: str) -> str | None:
    match = EQUIPMENT_TAG_PATTERN.search(text or "")
    return normalize_equipment_tag_match(match) if match else None


def extract_equipment_tag_candidates(text: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(normalize_equipment_tag_match(match) for match in EQUIPMENT_TAG_PATTERN.finditer(text or ""))
    )


__all__ = [
    "EQUIPMENT_TAG_PATTERN",
    "normalize_equipment_tag_match",
    "normalize_equipment_tag_text",
    "extract_equipment_tag_candidates",
]

"""MWO-LTSA-074 -- Normalization stage.

Pure dict-in/dict-out functions, deterministic (no wall-clock, no randomness,
no I/O). Reuses the exact text-cleaning discipline already established by
PRODUCTS/LTSA-BRAIN/INGESTION/ltsa_pump_inventory_ingestion.py::_clean_text
and ::_normalize_tag_number (collapse whitespace, blank/"-"/"N/A" -> None) --
this module does not reimplement Excel-serial date parsing (that belongs to
INGESTION's own workbook-specific ltsa_hoc_pm_cm_ingestion.py; this pipeline's
input is already-extracted JSON, never a spreadsheet cell), only the
whitespace/blank-value normalization that generalizes to any text field
regardless of source.
"""

from __future__ import annotations

import re
from typing import Any

_BLANK_TOKENS = {"", "-", "n/a", "na", "none", "null", "unknown"}


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()
    if text.casefold() in _BLANK_TOKENS:
        return None
    return text or None


def normalize_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    """Normalizes every string leaf value in a dict, recursively, never
    dropping a key (only cleaning its value) -- feeds the CanonicalKnowledge
    objects' own `raw` passthrough field, so nothing here should ever lose
    information the extraction genuinely provided."""
    if not value:
        return {}

    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, str):
            normalized[key] = normalize_text(item)
        elif isinstance(item, dict):
            normalized[key] = normalize_dict(item)
        elif isinstance(item, list):
            normalized[key] = [
                normalize_dict(entry) if isinstance(entry, dict) else
                (normalize_text(entry) if isinstance(entry, str) else entry)
                for entry in item
            ]
        else:
            normalized[key] = item
    return normalized


def normalize_list(value: list[Any] | None) -> list[dict[str, Any]]:
    if not value:
        return []
    return [normalize_dict(entry) if isinstance(entry, dict) else entry for entry in value]

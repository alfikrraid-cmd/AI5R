"""Canonical governed LTSA pump contract-area resolver.

Evidence-backed pump identities override raw-area token classification. Raw
area and maintenance area remain independent fields.
"""

from __future__ import annotations

UNCLASSIFIED = "Unclassified"

CONTRACT_AREA_GROUPS: tuple[str, ...] = ("HOC", "HSC & S. Pakning", "HCC", "OM & UTL")

_CONTRACT_AREA_BY_TOKEN: dict[str, str] = {
    "HOC": "HOC",
    "HSC": "HSC & S. Pakning",
    "SPK": "HSC & S. Pakning",
    "S_PAKNING": "HSC & S. Pakning",
    "HCC": "HCC",
    "OM": "OM & UTL",
    "UTL": "OM & UTL",
}

# Confirmed by physical CM/PM contract-scope evidence from April, June, and
# August 2026. This explicit map intentionally leaves unknown pump identities
# to the legacy exact-token resolver and ultimately Unclassified.
GOVERNED_PUMP_CONTRACT_AREA: dict[str, str] = {
    "101-P-2A": "HSC & S. Pakning",
    "100-P-6B": "HSC & S. Pakning",
    "200-P-1A": "HSC & S. Pakning",
    "301-P-12A": "HSC & S. Pakning",
    "110-P-1A": "OM & UTL",
    "920-P-2A": "OM & UTL",
    "110-P-2A": "HOC",
    "140-P-3A": "HOC",
    "220-P-1A": "HOC",
    "211-P-13AR": "HCC",
    "211-P-13BR": "HCC",
    "211-P-15C": "HCC",
    "211-P-1A": "HCC",
    "211-P-2A": "HCC",
    "211-P-8A": "HCC",
    "212-P-15C": "HCC",
    "212-P-4A": "HCC",
    "212-P-4B": "HCC",
    "212-P-7A": "HCC",
    "212-P-7B": "HCC",
    "212-P-8A": "HCC",
    "410-P-2A": "HCC",
    "701-P-1A": "HCC",
    "211-P-30": "HCC",
    "211-P-31": "HCC",
    "211-P-72A": "HCC",
    "211-P-72B": "HCC",
}

def resolve_contract_area(area: str | None, asset_code: str | None = None) -> str:
    """Resolve explicit governed pump evidence, then exact area tokens."""
    if asset_code in GOVERNED_PUMP_CONTRACT_AREA:
        return GOVERNED_PUMP_CONTRACT_AREA[asset_code]
    if area is None:
        return UNCLASSIFIED
    return _CONTRACT_AREA_BY_TOKEN.get(area, UNCLASSIFIED)


__all__ = [
    "resolve_contract_area",
    "CONTRACT_AREA_GROUPS",
    "GOVERNED_PUMP_CONTRACT_AREA",
    "UNCLASSIFIED",
]

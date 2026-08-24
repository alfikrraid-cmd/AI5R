"""MWO-LTSA-FLEET-CONTRACT-AREA-001 -- pure, explicit-token-only contract-area
classifier for the Fleet Overview.

Maps ONLY the 7 tokens confirmed authoritative this session (pump_area_scope.py's
own AREA_CODES {HOC,HSC,S_PAKNING,HCC,OM,UTL} plus the SPK alias
historical_pm_cmon_extraction.py's own _MA_BY_LOCATION dict already establishes)
to one of the 4 canonical LTSA contract groups. Every other raw `area` value --
including any process-unit/sub-area name, regardless of tag-number prefix or
same-prefix sibling evidence -- resolves to "Unclassified", never guessed.
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


def resolve_contract_area(area: str | None) -> str:
    """Explicit-token lookup only. Never infers from tag-number prefix,
    process-unit name, or any other signal -- an exact miss is Unclassified,
    not a best guess."""
    if area is None:
        return UNCLASSIFIED
    return _CONTRACT_AREA_BY_TOKEN.get(area, UNCLASSIFIED)


__all__ = ["resolve_contract_area", "CONTRACT_AREA_GROUPS", "UNCLASSIFIED"]

"""MWO-LTSA-AUTH-DATA-SCOPE-CLOSURE-001 -- backend-enforced pump data
scope by physical Area (HOC/HSC/S_PAKNING/HCC/OM/UTL) and MA supervisor
grouping, layered on the existing six-role LTSA auth
(API.auth_service.resolve_area_scope) rather than a second auth engine.

Area/MA is DATA SCOPE, not a role -- this module holds ONLY the
vocabulary and the generic filter/check primitives; it has no knowledge
of roles, tokens, or permissions (that stays in auth_service.py).

MA grouping: only MA2 (HSC + S_PAKNING + HCC) is included. MA1/MA3/MA4's
area membership could NOT be independently corroborated from any
authoritative repository source this session -- the only prior evidence
(historical_pm_cmon_extraction.py's own _MA_BY_LOCATION dict) is itself
traceable to a prior session's supplied business context, not a repo
artifact (ADR, migration, or other independent code). Per this MWO's own
"DO NOT GUESS... report unresolved mapping" instruction, MA1/MA3/MA4 are
deliberately NOT added here. A membership recorded with
data_scope_value in {'MA1','MA3','MA4'} resolves to an EMPTY scope
(auth_service.resolve_area_scope's own fail-closed default) rather than
being silently invented -- unresolved, never guessed.
"""

from __future__ import annotations

from typing import Any

# The six physical Area codes this MWO's own SCOPE RULES name explicitly.
AREA_CODES: frozenset[str] = frozenset({"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"})

# MA -> areas. Only MA2 is provable (given directly, as authoritative,
# in this MWO's own SCOPE RULES text: "MA2 = HSC + S_PAKNING + HCC").
MA_AREA_GROUPS: dict[str, frozenset[str]] = {
    "MA2": frozenset({"HSC", "S_PAKNING", "HCC"}),
}


def is_area_in_scope(area: str | None, scope: frozenset[str] | None) -> bool:
    """`scope` is the return value of auth_service.resolve_area_scope():
    None = unrestricted (always in scope); an empty/non-empty frozenset
    is checked by membership. A record with no area value at all is
    never in scope for a restricted identity -- never guessed as
    visible."""
    if scope is None:
        return True
    if area is None:
        return False
    return area in scope


def filter_records_by_scope(
    records: list[dict[str, Any]], scope: frozenset[str] | None, *, area_field: str = "area"
) -> list[dict[str, Any]]:
    """List/search enforcement: drops every record whose area_field value
    is not in scope. Used server-side, before a response leaves the
    backend -- frontend-only filtering does not satisfy this MWO's own
    "Backend enforcement required" rule."""
    if scope is None:
        return records
    return [r for r in records if is_area_in_scope(r.get(area_field), scope)]


__all__ = ["AREA_CODES", "MA_AREA_GROUPS", "is_area_in_scope", "filter_records_by_scope"]

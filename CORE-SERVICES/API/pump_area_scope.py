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


# MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- every LTSA domain OTHER
# than ltsa_pumps itself carries only an asset_code/pump-tag reference
# (work_order, maintenance_history, cm_report, pm_schedule,
# condition_monitoring_schedule/reading, pm_occurrence), never an `area`
# column of its own -- resolving scope for those records requires a
# 1-hop lookup back to the canonical pump. This reuses the EXACT same
# resolution routers/work_orders.py::get_ltsa_work_order_asset already
# established (pump_gateway.get_pump(asset_code) -> data["area"]) rather
# than inventing a second lookup path or trusting any client-supplied
# area value (Hard Rule: "Do NOT trust client-supplied area to authorize
# access").


def resolve_asset_area(asset_code: str | None, pump_gateway: Any) -> str | None:
    """Canonical asset_code -> area lookup. Returns None if asset_code is
    blank or the pump cannot be resolved -- callers must treat None as
    "not provably in any area" (denied for a restricted identity), never
    guessed or treated as unrestricted."""
    if not asset_code:
        return None
    try:
        response = pump_gateway.get_pump(asset_code)
    except Exception:
        return None
    if not isinstance(response, dict):
        return None
    data = response.get("data")
    if not isinstance(data, dict):
        return None
    return data.get("area")


class _AssetAreaCache:
    """Memoizes resolve_asset_area() within one request/list response --
    a list of N records referencing the same handful of pumps must not
    perform N redundant gateway round-trips for the same asset_code."""

    def __init__(self, pump_gateway: Any):
        self._pump_gateway = pump_gateway
        self._cache: dict[str, str | None] = {}

    def area_for(self, asset_code: str | None) -> str | None:
        if not asset_code:
            return None
        if asset_code not in self._cache:
            self._cache[asset_code] = resolve_asset_area(asset_code, self._pump_gateway)
        return self._cache[asset_code]


def is_asset_in_scope(asset_code: str | None, scope: frozenset[str] | None, pump_gateway: Any) -> bool:
    if scope is None:
        return True
    return is_area_in_scope(resolve_asset_area(asset_code, pump_gateway), scope)


def filter_records_by_asset_scope(
    records: list[dict[str, Any]],
    scope: frozenset[str] | None,
    pump_gateway: Any,
    *,
    asset_field: str = "asset_code",
) -> list[dict[str, Any]]:
    if scope is None:
        return records
    cache = _AssetAreaCache(pump_gateway)
    return [r for r in records if is_area_in_scope(cache.area_for(r.get(asset_field)), scope)]


__all__ = [
    "AREA_CODES",
    "MA_AREA_GROUPS",
    "is_area_in_scope",
    "filter_records_by_scope",
    "resolve_asset_area",
    "is_asset_in_scope",
    "filter_records_by_asset_scope",
]

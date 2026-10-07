"""MWO-LTSA-AUTH-DATA-SCOPE-CLOSURE-001 -- backend-enforced pump data
scope by physical Area (HOC/HSC/S_PAKNING/HCC/OM/UTL) and MA supervisor
grouping, layered on the existing six-role LTSA auth
(API.auth_service.resolve_area_scope) rather than a second auth engine.

Area/MA is DATA SCOPE, not a role -- this module holds ONLY the
vocabulary and the generic filter/check primitives; it has no knowledge
of roles, tokens, or permissions (that stays in auth_service.py).

MA grouping (MA_AREA_GROUPS below): MA1 = HOC, MA2 = HSC + S_PAKNING +
HCC, MA3 = UTL, MA4 = OM. (The original closure MWO shipped MA2 only; the
other three groups were added later -- this note previously still said
"only MA2".) An unrecognized MA value resolves to an EMPTY scope
(auth_service.resolve_area_scope's own fail-closed default), never
guessed.
"""

from __future__ import annotations

from typing import Any

# The six physical Area codes this MWO's own SCOPE RULES name explicitly.
AREA_CODES: frozenset[str] = frozenset({"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"})

# MA -> areas canonical grouping.
# MA1 = HOC
# MA2 = HSC + S_PAKNING + HCC
# MA3 = UTL
# MA4 = OM
MA_AREA_GROUPS: dict[str, frozenset[str]] = {
    "MA1": frozenset({"HOC"}),
    "MA2": frozenset({"HSC", "S_PAKNING", "HCC"}),
    "MA3": frozenset({"UTL"}),
    "MA4": frozenset({"OM"}),
}


_AREA_TOKEN_MAP: dict[str, str] = {
    "HOC": "HOC",
    "HSC": "HSC",
    "HCC": "HCC",
    "OM": "OM",
    "OIL MOVEMENT": "OM",
    "UTL": "UTL",
    "UTILITIES": "UTL",
    "S_PAKNING": "S_PAKNING",
    "S. PAKNING": "S_PAKNING",
    "S.PAKNING": "S_PAKNING",
    "S PAKNING": "S_PAKNING",
    "SPAKNING": "S_PAKNING",
    "SPK": "S_PAKNING",
}


def normalize_area_token(token: str | None) -> str | None:
    """Normalizes area query tokens (including aliases like SPK or human labels
    like S. PAKNING) to canonical stored Area code (e.g. S_PAKNING)."""
    if not token:
        return None
    import re
    cleaned = re.sub(r"\s+", " ", token.strip()).upper()
    return _AREA_TOKEN_MAP.get(cleaned)


def resolve_ma_areas(ma: str | None) -> frozenset[str] | None:
    """Returns the set of physical Area codes for a Maintenance Area (MA1-MA4),
    or None if unrecognized/blank."""
    if not ma:
        return None
    normalized = ma.strip().upper()
    return MA_AREA_GROUPS.get(normalized)


def resolve_area_ma(area: str | None) -> str | None:
    """Returns the Maintenance Area code ('MA1'..'MA4') for an Area code,
    or None if unrecognized/blank."""
    if not area:
        return None
    canonical = normalize_area_token(area) or area.strip().upper()
    for ma_key, areas in MA_AREA_GROUPS.items():
        if canonical in areas:
            return ma_key
    return None


def format_area_display(area: str | None) -> str:
    """Returns human display string for an Area code.
    S_PAKNING -> 'S. PAKNING'
    Unknown/blank -> 'N/A'"""
    if not area:
        return "N/A"
    canonical = normalize_area_token(area) or area.strip().upper()
    if canonical == "S_PAKNING":
        return "S. PAKNING"
    if canonical in AREA_CODES:
        return canonical
    return area.strip()


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
    canonical = normalize_area_token(area) or area.strip().upper()
    return canonical in scope


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


# LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- the Executive Dashboard's
# area filter narrows the caller's ALREADY-RESOLVED scope
# (auth_service.resolve_area_scope); it never widens it and is not a
# second authorization system. Only the six AREA_CODES are selectable:
# areas outside them (REAKTOR, FRAKSINASI, DCU, ...) stay reachable for
# unrestricted roles through "All Areas" only, exactly as before.

AREA_CODE_ORDER: tuple[str, ...] = ("HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL")

_AREA_LABELS: dict[str, str] = {"S_PAKNING": "S. Pakning"}


class InvalidAreaError(ValueError):
    """The requested area token does not normalize to an AREA_CODE."""


class AreaNotInScopeError(PermissionError):
    """The requested area is outside the caller's resolved scope."""


def resolve_requested_scope(
    user_scope: frozenset[str] | None, requested_area: str | None
) -> frozenset[str] | None:
    """Missing/"ALL" -> user_scope unchanged (None stays unrestricted, a
    finite or empty set stays exactly that). A specific area returns
    {canonical code} = intersection(user_scope, {code}); an unknown token
    raises InvalidAreaError and an area outside a finite scope (including
    the empty, fail-closed scope) raises AreaNotInScopeError."""
    if requested_area is None or not requested_area.strip() or requested_area.strip().upper() == "ALL":
        return user_scope
    code = normalize_area_token(requested_area)
    if code is None:
        raise InvalidAreaError(requested_area)
    if user_scope is not None and code not in user_scope:
        raise AreaNotInScopeError(code)
    return frozenset({code})


def area_label(code: str) -> str:
    return _AREA_LABELS.get(code, code)


def authorized_area_options(scope: frozenset[str] | None) -> list[dict[str, str]]:
    """The selectable areas for `scope` (resolve_area_scope's result), in
    AREA_CODE_ORDER. Unrestricted -> all six; finite -> its members; empty
    -> []."""
    allowed = AREA_CODES if scope is None else scope
    return [{"code": code, "label": area_label(code)} for code in AREA_CODE_ORDER if code in allowed]


def canonical_area_sql(column: str) -> str:
    """SQL expression mirroring is_area_in_scope's canonicalization
    (normalize_area_token, else the stripped upper-case raw value), built
    from _AREA_TOKEN_MAP itself so SQL and Python can never disagree on an
    alias (SPK, OIL MOVEMENT, UTILITIES, ...). `column` is a trusted,
    code-supplied identifier such as "p.area"."""
    token = f"upper(btrim(regexp_replace({column}, '\\s+', ' ', 'g')))"
    whens = " ".join(f"WHEN '{alias}' THEN '{code}'" for alias, code in _AREA_TOKEN_MAP.items())
    return f"(CASE {token} {whens} ELSE upper(btrim({column})) END)"


__all__ = [
    "AREA_CODES",
    "AREA_CODE_ORDER",
    "InvalidAreaError",
    "AreaNotInScopeError",
    "resolve_requested_scope",
    "area_label",
    "authorized_area_options",
    "canonical_area_sql",
    "MA_AREA_GROUPS",
    "resolve_ma_areas",
    "resolve_area_ma",
    "format_area_display",
    "normalize_area_token",
    "is_area_in_scope",
    "filter_records_by_scope",
    "resolve_asset_area",
    "is_asset_in_scope",
    "filter_records_by_asset_scope",
]

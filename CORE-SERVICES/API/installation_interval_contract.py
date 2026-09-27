"""LTSA_INSTALLATION_BASED_MTBF_R1 -- MTBF (Installation-based · Calendar
time): a TEMPORARY per-pump reliability proxy built only from completed
intervals between consecutive valid mechanical-seal installations. Pure
functions; no SQL, no persistence.

EVENTS: exactly current_installation_contract.valid_installation_events()
-- the same pump_tag_number attribution, date validation and structured
seal_location position the Current Installation contract uses. Nothing
else is a boundary: CM leaks, PM, inspections, findings, work orders,
configuration/API Plan/compatibility/stock changes never start or end an
interval. An installation is a proxy boundary, not a confirmed failure.

COMPLETED INTERVAL: previous -> next valid installation of the same pump
and the same position (DE->DE, NDE->NDE, pump-level->pump-level), in
report_date ASC order with installation_code ASC only as a tie-break.
Consecutive events on different positions are reported as non-comparable
transitions, never as intervals. A same-day pair is excluded as
unresolved (never a 0-day MTBF).

CALENDAR TIME: days = plant-local (Asia/Jakarta) date difference; hours =
days * 24 when either end is DATE_ONLY, exact elapsed hours only when both
ends are timestamps. Never actual operating hours.

CURRENT SERVICE AGE (latest installation -> today) is right-censored and
is NOT part of this metric; it stays in the Current Installation contract.

PUMP MTBF: arithmetic mean of the pump's completed comparable intervals;
null when there are none. Area/fleet rollups are deliberately not
provided here (R1 is pump-level only).
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Iterable

from .current_installation_contract import (
    PRECISION_DATE_ONLY,
    PRECISION_TIMESTAMP,
    TIME_BASIS_CALENDAR,
    InstallationEvent,
    parse_installation_moment,
    valid_installation_events,
)

POSITION_PUMP_LEVEL = "PUMP_LEVEL"

COMPARABLE = "COMPARABLE"
NON_COMPARABLE = "NON_COMPARABLE"
EXCLUDED_SAME_DAY = "EXCLUDED_SAME_DAY_UNRESOLVED"

IDENTITY_CONFIRMED_SAME = "CONFIRMED_SAME"
IDENTITY_CHANGED = "CHANGED"
IDENTITY_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class InstallationInterval:
    pump_tag: str
    position: str
    previous_installation_code: str
    previous_installation_date: str
    previous_seal_type: str | None
    previous_seal_size: str | None
    next_installation_code: str
    next_installation_date: str
    next_seal_type: str | None
    next_seal_size: str | None
    mtbf_days: int
    mtbf_hours: int
    seal_identity_status: str
    comparability_status: str
    time_basis: str = TIME_BASIS_CALENDAR
    precision: str = PRECISION_DATE_ONLY


@dataclass(frozen=True, slots=True)
class InstallationBasedMtbf:
    pump_tag: str
    installation_event_count: int
    completed_interval_count: int
    installation_based_mtbf_days: float | None
    installation_based_mtbf_hours: float | None
    intervals: tuple[InstallationInterval, ...]
    # Evidence the metric deliberately did not count, kept for audit.
    excluded_intervals: tuple[InstallationInterval, ...]
    non_comparable_transitions: tuple[InstallationInterval, ...]
    time_basis: str = TIME_BASIS_CALENDAR
    precision: str | None = None


def _position(event: InstallationEvent) -> str:
    return event.installation_position or POSITION_PUMP_LEVEL


def seal_identity_status(previous: InstallationEvent, following: InstallationEvent) -> str:
    """CHANGED when a recorded type or size differs; CONFIRMED_SAME only when
    both types are recorded and equal and the sizes are equal or both
    unrecorded; otherwise UNKNOWN. Missing values are never inferred."""
    types = (previous.installed_seal_type, following.installed_seal_type)
    sizes = (previous.installed_seal_size, following.installed_seal_size)
    if (None not in types and types[0] != types[1]) or (None not in sizes and sizes[0] != sizes[1]):
        return IDENTITY_CHANGED
    if None not in types and sizes[0] == sizes[1]:
        return IDENTITY_CONFIRMED_SAME
    return IDENTITY_UNKNOWN


def _interval(previous: InstallationEvent, following: InstallationEvent, status: str) -> InstallationInterval:
    start = parse_installation_moment(previous.installation_date)
    end = parse_installation_moment(following.installation_date)
    days = (end[0] - start[0]).days
    if start[2] == PRECISION_TIMESTAMP and end[2] == PRECISION_TIMESTAMP:
        precision, hours = PRECISION_TIMESTAMP, int((end[1] - start[1]).total_seconds() // 3600)
    else:
        precision, hours = PRECISION_DATE_ONLY, days * 24
    same_position = _position(previous) == _position(following)
    return InstallationInterval(
        pump_tag=previous.pump_tag_number,
        position=_position(previous) if same_position else f"{_position(previous)}->{_position(following)}",
        previous_installation_code=previous.installation_code,
        previous_installation_date=previous.installation_date,
        previous_seal_type=previous.installed_seal_type,
        previous_seal_size=previous.installed_seal_size,
        next_installation_code=following.installation_code,
        next_installation_date=following.installation_date,
        next_seal_type=following.installed_seal_type,
        next_seal_size=following.installed_seal_size,
        mtbf_days=days,
        mtbf_hours=hours,
        seal_identity_status=seal_identity_status(previous, following),
        comparability_status=status,
        precision=precision,
    )


def installation_based_mtbf(records: Iterable[dict[str, Any]], tag_number: str) -> InstallationBasedMtbf:
    events = list(reversed(valid_installation_events(records, tag_number)))  # date ASC, code ASC

    transitions = tuple(
        _interval(a, b, NON_COMPARABLE) for a, b in zip(events, events[1:]) if _position(a) != _position(b)
    )

    by_position: dict[str, list[InstallationEvent]] = {}
    for event in events:
        by_position.setdefault(_position(event), []).append(event)

    completed: list[InstallationInterval] = []
    excluded: list[InstallationInterval] = []
    for group in by_position.values():
        for a, b in zip(group, group[1:]):
            same_day = parse_installation_moment(a.installation_date)[0] == parse_installation_moment(b.installation_date)[0]
            if same_day:
                excluded.append(_interval(a, b, EXCLUDED_SAME_DAY))
            else:
                completed.append(_interval(a, b, COMPARABLE))
    completed.sort(key=lambda i: (i.next_installation_date, i.next_installation_code))

    mtbf_days = round(mean(i.mtbf_days for i in completed), 1) if completed else None
    mtbf_hours = round(mean(i.mtbf_hours for i in completed), 1) if completed else None
    precision = None
    if completed:
        precision = PRECISION_DATE_ONLY if any(i.precision == PRECISION_DATE_ONLY for i in completed) else PRECISION_TIMESTAMP

    return InstallationBasedMtbf(
        pump_tag=tag_number,
        installation_event_count=len(events),
        completed_interval_count=len(completed),
        installation_based_mtbf_days=mtbf_days,
        installation_based_mtbf_hours=mtbf_hours,
        intervals=tuple(completed),
        excluded_intervals=tuple(excluded),
        non_comparable_transitions=transitions,
        precision=precision,
    )


__all__ = [
    "COMPARABLE",
    "EXCLUDED_SAME_DAY",
    "IDENTITY_CHANGED",
    "IDENTITY_CONFIRMED_SAME",
    "IDENTITY_UNKNOWN",
    "InstallationBasedMtbf",
    "InstallationInterval",
    "NON_COMPARABLE",
    "POSITION_PUMP_LEVEL",
    "installation_based_mtbf",
    "seal_identity_status",
]

"""LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1 -- the one
canonical CURRENT INSTALLATION contract for a pump's mechanical seal, and
its calendar-time service age. Pure functions over already-fetched rows:
no SQL, no gateway, no persistence (the counters are never stored).

ATTRIBUTION: an installation_report belongs to a pump only through its
governed installation_report.pump_tag_number
(MWO-LTSA-INSTALLATION-REPORT-HISTORICAL-ATTRIBUTION-001), never the
free-text plant_equip_no transcription (production: 5 of 42 reports carry
an annotated or sibling pump there, e.g. INSTL-025 plant_equip_no
101-P-2A for pump 101-P-3B).

VALID INSTALLATION: attributed to the pump and a report_date that is a
real ISO calendar date (YYYY-MM-DD) or an ISO timestamp. The caller's
repository query additionally requires pump_tag_number to resolve to an
asset_registry PUMP.

POSITION: DE/NDE only when installation_report.seal_location explicitly
records it. Never inferred from free text (plant_equip_no suffixes,
source file names). An unpositioned installation is pump-level.

SUPERSESSION: per (pump, position) key, the latest valid installation is
current; ties on the same date break on installation_code DESC. A later
lifecycle REMOVE/SCRAP/RETURN_TO_STOCK for the pump (seal_lifecycle_event,
no position column, so it applies to every position) ends the
installation: status REMOVED, the counter stops.

CONFIGURED/DESIGN data (ltsa_pumps.seal_type), compatibility and stock
application rows are never read here -- they are not installation
evidence.

SERVICE AGE is CALENDAR TIME, never operating/running hours:
  days  = plant-local (Asia/Jakarta) calendar date difference
  hours = days * 24 when the installation is DATE_ONLY (no installation
          time-of-day is claimed); the exact elapsed hours only for a
          TIMESTAMP-precision installation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

# Asia/Jakarta is WIB, a fixed UTC+07:00 with no daylight saving (since
# 1964), so a fixed offset is exact and needs no tz database on the host.
PLANT_TIMEZONE_NAME = "Asia/Jakarta"
PLANT_TIMEZONE = timezone(timedelta(hours=7), PLANT_TIMEZONE_NAME)

STATUS_INSTALLED = "INSTALLED"
STATUS_NOT_RECORDED = "NOT_RECORDED"
STATUS_REMOVED = "REMOVED"

TIME_BASIS_CALENDAR = "CALENDAR_TIME"
PRECISION_DATE_ONLY = "DATE_ONLY"
PRECISION_TIMESTAMP = "TIMESTAMP"

POSITIONS = frozenset({"DE", "NDE"})
REMOVAL_EVENT_TYPES = frozenset({"REMOVE", "SCRAP", "RETURN_TO_STOCK"})

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class InstallationEvent:
    installation_code: str
    pump_tag_number: str
    installation_date: str
    time_precision: str
    installation_position: str | None
    installed_seal_type: str | None
    # R1.1 -- this report's own installation_report.seal_size, source text
    # verbatim (trimmed only; e.g. 4.1/2", 2.375", 55 MM). Never normalized,
    # never taken from the catalog, compatibility, stock or a sibling report.
    installed_seal_size: str | None
    installed_seal_unit: str | None
    seal_code: str | None
    report_no: str | None
    source_document: str | None


@dataclass(frozen=True, slots=True)
class CurrentInstallation:
    installation_status: str
    installed_seal_type: str | None = None
    installed_seal_size: str | None = None
    installed_seal_unit: str | None = None
    seal_code: str | None = None
    installation_date: str | None = None
    installation_position: str | None = None
    source_document: str | None = None
    source_installation_code: str | None = None
    removed_at: str | None = None
    time_since_installation_days: int | None = None
    time_since_installation_hours: int | None = None
    time_basis: str = TIME_BASIS_CALENDAR
    time_precision: str | None = None
    # No runtime/hour-meter source exists anywhere in the schema.
    actual_operating_hours: None = None


NOT_RECORDED = CurrentInstallation(installation_status=STATUS_NOT_RECORDED)


@dataclass(frozen=True, slots=True)
class InstallationResolution:
    current: CurrentInstallation
    current_by_position: tuple[CurrentInstallation, ...] = ()
    history: tuple[InstallationEvent, ...] = field(default_factory=tuple)


def plant_now(now: datetime | None = None) -> datetime:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("plant_now requires a timezone-aware datetime")
    return moment.astimezone(PLANT_TIMEZONE)


def plant_today(now: datetime | None = None) -> date:
    return plant_now(now).date()


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_installation_moment(raw: Any) -> tuple[date, datetime | None, str] | None:
    """(plant-local date, aware timestamp or None, precision) or None when
    the value is not a valid calendar date/timestamp."""
    text = _clean(raw)
    if text is None:
        return None
    if _ISO_DATE.match(text):
        try:
            return date.fromisoformat(text), None, PRECISION_DATE_ONLY
        except ValueError:
            return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        # A time with no zone cannot be placed on the plant clock.
        return None
    local = moment.astimezone(PLANT_TIMEZONE)
    return local.date(), local, PRECISION_TIMESTAMP


def installation_position(record: dict[str, Any]) -> str | None:
    location = _clean(record.get("seal_location"))
    if location is None:
        return None
    upper = location.upper()
    return upper if upper in POSITIONS else None


def valid_installation_events(records: Iterable[dict[str, Any]], tag_number: str) -> tuple[InstallationEvent, ...]:
    """Valid events for this pump, newest first (date DESC, code DESC)."""
    events: list[tuple[date, str, InstallationEvent]] = []
    for record in records:
        if record.get("pump_tag_number") != tag_number:
            continue
        code = _clean(record.get("installation_code"))
        parsed = parse_installation_moment(record.get("report_date"))
        if code is None or parsed is None:
            continue
        local_date, moment, precision = parsed
        events.append(
            (
                local_date,
                code,
                InstallationEvent(
                    installation_code=code,
                    pump_tag_number=tag_number,
                    installation_date=moment.isoformat() if moment is not None else local_date.isoformat(),
                    time_precision=precision,
                    installation_position=installation_position(record),
                    installed_seal_type=_clean(record.get("seal_type")),
                    installed_seal_size=_clean(record.get("seal_size")),
                    installed_seal_unit=_clean(record.get("seal_unit_id")),
                    seal_code=_clean(record.get("seal_code")),
                    report_no=_clean(record.get("report_no")),
                    source_document=_clean(record.get("source_document_name")),
                ),
            )
        )
    events.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return tuple(event for _, _, event in events)


def _removal_dates(removal_events: Iterable[dict[str, Any]], tag_number: str) -> list[date]:
    dates: list[date] = []
    for event in removal_events:
        if event.get("event_type") not in REMOVAL_EVENT_TYPES or event.get("pump_tag_number") != tag_number:
            continue
        parsed = parse_installation_moment(event.get("event_at"))
        if parsed is not None:
            dates.append(parsed[0])
    return dates


def service_age(event: InstallationEvent, *, now: datetime) -> tuple[int | None, int | None]:
    """(days, hours) of calendar time since installation; (None, None) for
    evidence dated after `now` (never a negative age)."""
    parsed = parse_installation_moment(event.installation_date)
    if parsed is None:
        return None, None
    local_date, moment, precision = parsed
    local_now = plant_now(now)
    days = (local_now.date() - local_date).days
    if days < 0:
        return None, None
    if precision == PRECISION_TIMESTAMP and moment is not None:
        elapsed = local_now - moment
        if elapsed.total_seconds() < 0:
            return None, None
        return days, int(elapsed.total_seconds() // 3600)
    return days, days * 24


def _current_from_event(
    event: InstallationEvent, *, removal_dates: list[date], now: datetime
) -> CurrentInstallation:
    installed_on = parse_installation_moment(event.installation_date)[0]  # type: ignore[index]
    later_removals = sorted(d for d in removal_dates if d > installed_on)
    if later_removals:
        return CurrentInstallation(
            installation_status=STATUS_REMOVED,
            installation_position=event.installation_position,
            source_installation_code=event.installation_code,
            removed_at=later_removals[0].isoformat(),
        )
    days, hours = service_age(event, now=now)
    return CurrentInstallation(
        installation_status=STATUS_INSTALLED,
        installed_seal_type=event.installed_seal_type,
        installed_seal_size=event.installed_seal_size,
        installed_seal_unit=event.installed_seal_unit,
        seal_code=event.seal_code,
        installation_date=event.installation_date,
        installation_position=event.installation_position,
        source_document=event.source_document,
        source_installation_code=event.installation_code,
        time_since_installation_days=days,
        time_since_installation_hours=hours,
        time_precision=event.time_precision,
    )


def resolve_current_installation(
    records: Iterable[dict[str, Any]],
    tag_number: str,
    *,
    removal_events: Iterable[dict[str, Any]] = (),
    now: datetime | None = None,
) -> InstallationResolution:
    moment = plant_now(now)
    history = valid_installation_events(records, tag_number)
    if not history:
        return InstallationResolution(current=NOT_RECORDED, current_by_position=(), history=())

    removal_dates = _removal_dates(removal_events, tag_number)
    latest_by_position: dict[str | None, InstallationEvent] = {}
    for event in history:  # newest first: first seen per key is current
        latest_by_position.setdefault(event.installation_position, event)

    # Primary = the newest current installation across positions (history
    # order), so the header shows the most recent evidence.
    ordered = [event for event in history if latest_by_position.get(event.installation_position) is event]
    currents = tuple(_current_from_event(event, removal_dates=removal_dates, now=moment) for event in ordered)
    return InstallationResolution(current=currents[0], current_by_position=currents, history=history)


__all__ = [
    "CurrentInstallation",
    "InstallationEvent",
    "InstallationResolution",
    "NOT_RECORDED",
    "PLANT_TIMEZONE",
    "PLANT_TIMEZONE_NAME",
    "PRECISION_DATE_ONLY",
    "PRECISION_TIMESTAMP",
    "STATUS_INSTALLED",
    "STATUS_NOT_RECORDED",
    "STATUS_REMOVED",
    "TIME_BASIS_CALENDAR",
    "plant_today",
    "resolve_current_installation",
    "service_age",
    "valid_installation_events",
]

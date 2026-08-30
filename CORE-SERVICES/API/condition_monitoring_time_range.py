"""MWO-LTSA-CMON-DETAILED-HISTORY-001 -- deterministic parsing of the
relative/explicit time-range phrasings a CMON history question can use
("setahun terakhir", "3 bulan terakhir", "sejak Januari 2026", "tahun
2026"). Pure function of (text, today) -- no I/O, no LLM, fully
deterministic and independently testable.

Returns None when the question names no time range at all (a bare
"riwayat CMON <tag>" / "history CMON <tag>") -- callers use that to mean
"no date filter", never "latest only" and never a silently-invented
default window (this MWO's own explicit rule: no existing safe default
history window is defined anywhere in this codebase, confirmed by
repository archaeology before writing this module -- inventing one here
would be exactly the kind of undisclosed business rule this MWO forbids).
"""

from __future__ import annotations

import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class ConditionMonitoringPeriod:
    start: date
    end: date
    label_id: str
    label_en: str


_MONTH_NAMES = {
    "januari": 1, "january": 1, "jan": 1,
    "februari": 2, "february": 2, "feb": 2,
    "maret": 3, "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "june": 6, "jun": 6,
    "juli": 7, "july": 7, "jul": 7,
    "agustus": 8, "august": 8, "aug": 8, "agu": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "october": 10, "okt": 10, "oct": 10,
    "november": 11, "nov": 11,
    "desember": 12, "december": 12, "des": 12, "dec": 12,
}
_MONTH_PATTERN = "|".join(sorted(_MONTH_NAMES, key=len, reverse=True))


def _subtract_months(d: date, months: int) -> date:
    month_index = d.month - 1 - months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def _subtract_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        # Feb 29 on a non-leap target year -- fall back to Feb 28, the
        # same "nearest valid day" convention _subtract_months already
        # uses via monthrange's own day-clamping.
        return d.replace(year=d.year - years, day=28)


def parse_condition_monitoring_period(text: str, today: date | None = None) -> ConditionMonitoringPeriod | None:
    today = today or date.today()
    lowered = (text or "").casefold()

    # "setahun terakhir" / "1 tahun terakhir" / "N tahun terakhir"
    match = re.search(r"(\d+)\s*tahun\s+terakhir", lowered)
    if match:
        years = int(match.group(1))
        start = _subtract_years(today, years)
        label = f"{years} Tahun Terakhir" if years != 1 else "1 Tahun Terakhir"
        return ConditionMonitoringPeriod(start, today, label, label.replace("Tahun", "Year(s)"))
    if re.search(r"\bsetahun\s+terakhir\b", lowered):
        start = _subtract_years(today, 1)
        return ConditionMonitoringPeriod(start, today, "1 Tahun Terakhir", "Last 1 Year")

    # "N bulan terakhir"
    match = re.search(r"(\d+)\s*bulan\s+terakhir", lowered)
    if match:
        months = int(match.group(1))
        start = _subtract_months(today, months)
        label_id = f"{months} Bulan Terakhir"
        label_en = f"Last {months} Month(s)"
        return ConditionMonitoringPeriod(start, today, label_id, label_en)

    # "sejak <month> [<year>]"
    match = re.search(rf"\bsejak\s+({_MONTH_PATTERN})\s*(\d{{4}})?", lowered)
    if match:
        month = _MONTH_NAMES[match.group(1)]
        year = int(match.group(2)) if match.group(2) else today.year
        start = date(year, month, 1)
        label_id = f"Sejak {match.group(1).capitalize()} {year}"
        label_en = f"Since {match.group(1).capitalize()} {year}"
        return ConditionMonitoringPeriod(start, today, label_id, label_en)

    # "sejak <YYYY-MM-DD>" or "sejak <DD-MM-YYYY>"-free explicit ISO date
    match = re.search(r"\bsejak\s+(\d{4})-(\d{2})-(\d{2})", lowered)
    if match:
        start = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        label = f"Sejak {start.isoformat()}"
        return ConditionMonitoringPeriod(start, today, label, f"Since {start.isoformat()}")

    # "tahun <YYYY>" (bare year, no "terakhir"/"sejak") -- the whole
    # calendar year, bounded to today when the requested year is the
    # current year (no future dates in a real result set anyway, but the
    # requested/interpreted period itself must not claim to extend past
    # today).
    match = re.search(r"\btahun\s+(\d{4})\b", lowered)
    if match:
        year = int(match.group(1))
        start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        end = min(year_end, today) if year == today.year else year_end
        label = f"Tahun {year}"
        return ConditionMonitoringPeriod(start, end, label, f"Year {year}")

    return None


__all__ = ["ConditionMonitoringPeriod", "parse_condition_monitoring_period"]

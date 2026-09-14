"""MWO-LTSA-CONTRACT-SCOPE-R3 -- Contract Coverage computation (Chief
Architect approved design, R2/R3). One Aggregate, reused by both the
assets and coverage endpoints -- same "One Aggregate, One API" discipline
FleetReliabilityService/BasicFleetOverviewService already establish
(routers/fleet.py), so the frontend never recreates this business logic
(R3 Section E's own explicit rule).

Deterministic-only. Every field this service returns is either directly
proven by ltsa_contract_asset_scope/asset_registry/condition_monitoring_reading,
or explicitly null/N/A when the authoritative data does not exist yet
(monitoring_required/overdue, per R2 decision 9 -- condition_monitoring_
schedule has zero populated rows in this environment; NEVER return 0 as
if zero monitoring were required, and NEVER silently return the number of
readings the way TOTAL_CONTRACT_ASSETS could be confused for)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from .pump_area_scope import is_area_in_scope, resolve_area_ma

if TYPE_CHECKING:
    from .ltsa_contract_repository import LtsaContractRepository

MA_BUCKET_KEYS = ("MA1", "MA2", "MA3", "MA4", "UNMAPPED")


class InvalidReportingPeriod(ValueError):
    """period_start > period_end, or either is not a valid ISO date."""


class ContractNotFound(LookupError):
    pass


def _ma_bucket(area: str | None) -> str:
    ma = resolve_area_ma(area)
    return ma if ma in ("MA1", "MA2", "MA3", "MA4") else "UNMAPPED"


def _validate_period(period_start: str, period_end: str) -> None:
    try:
        start = date.fromisoformat(period_start)
        end = date.fromisoformat(period_end)
    except (TypeError, ValueError) as exc:
        raise InvalidReportingPeriod(f"period_start/period_end must be ISO dates (YYYY-MM-DD): {exc}") from exc
    if start > end:
        raise InvalidReportingPeriod("period_start must be <= period_end")


@dataclass
class ContractAssetRow:
    asset_code: str
    asset_type: str | None
    area: str | None
    ma: str
    scope_start_date: str | None
    scope_end_date: str | None
    effective_scope_start: str
    effective_scope_end: str
    last_cm_date: str | None
    cm_reading_count_in_period: int
    monitoring_status: str  # "MONITORED" | "PENDING"


@dataclass
class MABucketCoverage:
    total_contract_assets: int
    monitored: int
    pending: int
    coverage_percent: float | None
    monitoring_required: None = None
    overdue: None = None


@dataclass
class ContractCoverage:
    contract_code: str
    period_start: str
    period_end: str
    total_contract_assets: int
    monitored: int
    pending: int
    coverage_percent: float | None
    by_ma: dict[str, MABucketCoverage]
    monitoring_required: None = None
    overdue: None = None


def _coverage_percent(monitored: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(monitored / total * 100, 1)


class ContractCoverageService:
    def __init__(self, repository: "LtsaContractRepository") -> None:
        self._repository = repository

    def _load_asset_rows(
        self,
        contract_code: str,
        period_start: str,
        period_end: str,
        *,
        scope: frozenset[str] | None = None,
    ) -> list[ContractAssetRow]:
        _validate_period(period_start, period_end)

        contract = self._repository.find_contract(contract_code)
        if contract is None:
            raise ContractNotFound(contract_code)

        scoped = self._repository.list_scoped_assets_in_period(contract_code, period_start, period_end)
        # MWO-LTSA-AUTH-DATA-SCOPE-CLOSURE-001 -- same backend-enforced
        # Area/MA data scope every other LTSA list endpoint already
        # applies (pumps.py's own filter_records_by_scope); a Pertamina
        # identity restricted to certain areas must never see contract
        # assets/coverage counts outside that scope, regardless of what
        # the client requests.
        if scope is not None:
            scoped = [row for row in scoped if is_area_in_scope(row.get("area"), scope)]
        asset_codes = [row["asset_code"] for row in scoped]
        monitoring = self._repository.monitoring_summary_by_asset(asset_codes, period_start, period_end)

        rows: list[ContractAssetRow] = []
        for row in scoped:
            summary = monitoring.get(row["asset_code"], {})
            reading_count = summary.get("reading_count_in_period") or 0
            rows.append(
                ContractAssetRow(
                    asset_code=row["asset_code"],
                    asset_type=row.get("asset_type"),
                    area=row.get("area"),
                    ma=_ma_bucket(row.get("area")),
                    scope_start_date=row.get("scope_start_date"),
                    scope_end_date=row.get("scope_end_date"),
                    effective_scope_start=row["effective_scope_start"],
                    effective_scope_end=row["effective_scope_end"],
                    last_cm_date=summary.get("last_reading_date_all_time"),
                    cm_reading_count_in_period=reading_count,
                    monitoring_status="MONITORED" if reading_count >= 1 else "PENDING",
                )
            )
        return rows

    def list_assets(
        self, contract_code: str, period_start: str, period_end: str, *, scope: frozenset[str] | None = None
    ) -> list[ContractAssetRow]:
        return self._load_asset_rows(contract_code, period_start, period_end, scope=scope)

    def build_coverage(
        self, contract_code: str, period_start: str, period_end: str, *, scope: frozenset[str] | None = None
    ) -> ContractCoverage:
        rows = self._load_asset_rows(contract_code, period_start, period_end, scope=scope)

        total = len(rows)
        monitored = sum(1 for r in rows if r.monitoring_status == "MONITORED")
        pending = total - monitored

        by_ma: dict[str, MABucketCoverage] = {}
        for bucket in MA_BUCKET_KEYS:
            bucket_rows = [r for r in rows if r.ma == bucket]
            bucket_total = len(bucket_rows)
            bucket_monitored = sum(1 for r in bucket_rows if r.monitoring_status == "MONITORED")
            by_ma[bucket] = MABucketCoverage(
                total_contract_assets=bucket_total,
                monitored=bucket_monitored,
                pending=bucket_total - bucket_monitored,
                coverage_percent=_coverage_percent(bucket_monitored, bucket_total),
            )

        # Reconciliation invariant (R3 Section D): every scoped asset
        # belongs to exactly one bucket, so the buckets must sum back to
        # the whole -- asserted here, not just tested, so a future MA
        # mapping change that silently drops an asset fails loudly rather
        # than shipping a coverage number that doesn't add up.
        assert sum(b.total_contract_assets for b in by_ma.values()) == total, (
            "MA bucket reconciliation failed: by_ma totals do not sum to total_contract_assets"
        )

        return ContractCoverage(
            contract_code=contract_code,
            period_start=period_start,
            period_end=period_end,
            total_contract_assets=total,
            monitored=monitored,
            pending=pending,
            coverage_percent=_coverage_percent(monitored, total),
            by_ma=by_ma,
        )


__all__ = [
    "ContractCoverageService",
    "ContractAssetRow",
    "MABucketCoverage",
    "ContractCoverage",
    "ContractNotFound",
    "InvalidReportingPeriod",
    "MA_BUCKET_KEYS",
]

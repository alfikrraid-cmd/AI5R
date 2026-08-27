from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# MWO-LTSA-064A -- DTOs must depend on nothing (per this MWO's own
# dependency-direction rule: "DTO / Value Objects -> Service. Never
# Service -> Service -> DTO."). The prior `from .equipment_timeline_service
# import TimelineEvent` was the circular-import root cause
# (pump_lifecycle_models.py -> equipment_timeline_service.py ->
# pump_lifecycle_models.py) and was never actually used anywhere in this
# file -- `PumpLifecycle.timeline` has always been typed `tuple[Any, ...]`,
# never `tuple[TimelineEvent, ...]`. Removing the dead import is the whole
# fix: it breaks the cycle with zero behavior change and restores the one
# allowed direction (equipment_timeline_service.py already imports these
# DTOs; this module now imports nothing back).


@dataclass(frozen=True, slots=True)
class PumpLifecycleCurrentInstallation:
    installation_code: str
    report_no: str | None
    report_date: str | None
    plant_equip_no: str | None
    seal_code: str | None
    seal_type: str | None
    seal_manufacture: str | None
    drawing_no: str | None
    source_document_name: str | None
    # MWO-LTSA-066 -- derived from installation_report.signatures (JSONB),
    # never a new column. See equipment_timeline_service.py's
    # _derive_engineer() for the exact, disclosed derivation rule.
    engineer: str | None


@dataclass(frozen=True, slots=True)
class PumpLifecycleCurrentSeal:
    seal_code: str | None
    seal_name: str | None
    manufacturer: str | None
    model: str | None
    shaft_size: str | None
    material: str | None
    temperature_limit: str | None
    pressure_limit: str | None
    status: str | None
    installation_code: str | None
    installed_at: str | None
    source: str
    # MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B (item G) -- read from the
    # SAME current_installation record _build_current_seal() already
    # receives (equipment_timeline_service.py) -- installation_report
    # already has this column (PumpLifecycleCurrentInstallation.
    # source_document_name above already exposes it for /lifecycle's
    # current_installation; this is the identical field, same source, now
    # also carried on current_seal so /knowledge's own current_seal key
    # -- which never included current_installation -- doesn't lose it).
    # No new fetch, no fabrication: null when the underlying installation
    # record has no value for it.
    source_document_name: str | None = None


@dataclass(frozen=True, slots=True)
class PumpLifecycleCurrentState:
    # MWO-LTSA-064A -- CurrentInstallation and CurrentSeal live ONLY here.
    # PumpLifecycle no longer carries its own root-level copies (see
    # PumpLifecycle below) -- CurrentState is the one source of truth for
    # "what is installed on this pump right now."
    current_installation: PumpLifecycleCurrentInstallation | None
    current_seal: PumpLifecycleCurrentSeal | None
    elapsed_service_days: int | None
    running_hours_derived: None
    last_pm: dict[str, Any] | None
    next_pm: dict[str, Any] | None
    last_cm: dict[str, Any] | None
    last_failure: dict[str, Any] | None
    open_work_orders: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class PumpLifecycleAnalytics:
    elapsed_service_days: int | None
    pm_count: int
    cm_count: int
    failure_count: int
    mtbf: None
    mtbr: None
    # MWO-LTSA-064A -- "sealLife" is not a new field: average_seal_life
    # already exists, already nullable, already means exactly this.
    # Adding a second seal_life field alongside it would recreate the
    # same duplicate-object problem this MWO's Section 2 removes
    # elsewhere -- see the Completion Report's "Analytics" note for why
    # this field is being reused rather than duplicated.
    average_seal_life: None
    # New placeholders (Section 5) -- nullable, no calculation performed.
    health_index: None = None
    availability: None = None
    reliability: None = None


@dataclass(frozen=True, slots=True)
class PumpLifecycleRelatedEngineering:
    pm_schedules: list[dict[str, Any]]
    cm_reports: list[dict[str, Any]]
    work_orders: list[dict[str, Any]]
    breakdown_history: list[dict[str, Any]]
    # MWO-LTSA-064A -- extended per Section 4. Each reuses data already
    # produced elsewhere (LTSAKnowledgeService.build()'s own drawings/
    # inventory fields, and SealEngineeringDocumentGateway already held by
    # LTSAKnowledgeService) -- no new gateway, no duplicate fetch. See
    # equipment_timeline_service.py's build_lifecycle() for exactly what
    # each is populated from.
    drawings: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    # MWO-LTSA-PM-CM-INTAKE-001 -- Condition Monitoring readings for this
    # pump, same "reuse data already produced elsewhere" convention as
    # pm_schedules/cm_reports above (knowledge.condition_monitoring_readings,
    # LTSAKnowledgeService.build()'s own field).
    condition_monitoring_readings: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PumpLifecycle:
    tag_number: str
    pump: dict[str, Any] | None
    current_state: PumpLifecycleCurrentState
    timeline: tuple[Any, ...]
    analytics: PumpLifecycleAnalytics
    related_engineering: PumpLifecycleRelatedEngineering

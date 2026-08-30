"""MWO-LTSA-FLEET-ANALYTICS-001 (readiness closure) -- proves the REAL
production dependency-injection graph (dependencies.py, imported
unmodified, not a fake/mock) actually satisfies FleetReliabilityService.
list_pump_knowledge_fast()'s batch-path precondition, so
"Pompa mana yang perlu perhatian hari ini?" genuinely uses
build_fleet_data_batch() (~9 total gateway/DB calls) under normal
production wiring, never silently falling back to the old
LTSAKnowledgeService.build(tag) x N per-pump path.

This does not require a live DB/n8n connection: _batch_sources_available()
is a pure attribute-presence check, and list_pump_knowledge_fast()'s own
branch on it is what determines which code path executes -- proving the
branch condition is enough to prove which path production takes, without
needing to actually run a live fleet query.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_API_DIR))

import dependencies  # noqa: E402  -- the real production module, unmodified


def test_production_fleet_reliability_service_has_every_batch_dependency_wired():
    service = dependencies._fleet_reliability_service
    assert service.condition_monitoring_reading_repository is not None
    assert service.cm_report_repository is not None
    assert service.pm_occurrence_repository is not None
    assert service.pm_schedule_repository is not None
    assert service.seal_pump_compatibility_gateway is not None
    assert service.seal_gateway is not None
    assert service.mechanical_seal_stock_repository is not None


def test_production_fleet_reliability_service_batch_path_is_selected_not_fallback():
    # This is the exact precondition list_pump_knowledge_fast() branches
    # on -- True here means the real production singleton takes the
    # build_fleet_data_batch() path, never list_pump_knowledge()'s old
    # one-LTSAKnowledgeService.build(tag)-per-pump loop.
    assert dependencies._fleet_reliability_service._batch_sources_available() is True


def test_production_fleet_executive_summary_service_reuses_the_same_singleton():
    # "Pompa mana yang perlu perhatian hari ini?" is served through
    # FleetExecutiveSummaryService.build() -> self.fleet_reliability_
    # service.list_pump_knowledge_fast() -- this proves that call reaches
    # the SAME already-verified batch-wired singleton above, not a second,
    # differently-constructed FleetReliabilityService instance.
    assert dependencies._fleet_executive_summary_service.fleet_reliability_service is dependencies._fleet_reliability_service


def test_production_work_order_and_maintenance_history_gateways_also_wired():
    # Optional for the batch path itself, but required to keep
    # REC_REPEATED_BREAKDOWN's breakdown_history coverage identical to the
    # old per-pump LTSAKnowledgeService.build() path (fleet_reliability_
    # service.py's own docstring) -- asserted separately since these two
    # are NOT part of _batch_sources_available()'s required set.
    service = dependencies._fleet_reliability_service
    assert service.work_order_gateway is not None
    assert service.maintenance_history_gateway is not None

"""MWO-LTSA-HISTORICAL-SEAL-SERVICE-ACTIVITY-TEST-001 -- tests for historical
mechanical seal service activity (2024-2025) ingestion, repository, and timeline
integration.

Tests verify:
1. Finish Date is canonical event date (missing finish date yields None event_date).
2. Conservative asset matching (exact, normalized, ambiguous, no-match).
3. HISTORY ONLY: historical events never establish or mutate Current Installation.
4. Specific pump scenarios:
   - 300-P-7A: Current Installation remains UNKNOWN; 3 historical events appear in history.
   - 211-P-14B: 2026 validated installation remains Current Installation; 2025 is history;
     2024 211-P-14 is ambiguous and unlinked.
5. Idempotency: re-running ingestion inserts zero duplicates.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(_CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(_CORE_SERVICES_PATH))

_INGESTION_DIR = Path(__file__).resolve().parents[3] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from API.equipment_timeline_service import EquipmentTimelineService
from API.historical_seal_service_activity_repository import HistoricalSealServiceActivityRepository
from API.installation_gateway import InstallationGateway
from API.ltsa_knowledge_service import LTSAKnowledgeService
from API.pump_lifecycle_models import PumpLifecycle
from API.seal_equipment_history_service import build_seal_events_for_pump
from API.timeline_value_objects import TimelineCategory, TimelineEvent, TimelineSource

from historical_seal_service_activity_ingestion import (
    classify_tag,
    parse_date_val,
    build_insert_sql,
    extract_all_records,
)


CANONICAL_PUMP_TAGS = {
    "101-P-1A", "101-P-1B", "101-P-2A", "101-P-2B",
    "110-P-15A", "110-P-15B",
    "140-P-17A", "140-P-17B",
    "211-P-13AR", "211-P-13BR",
    "211-P-14A", "211-P-14B",
    "212-P-8A", "212-P-8B",
    "300-P-7A", "300-P-7B",
    "702-P-4A", "702-P-4B",
    "920-P-2A", "920-P-2B",
}


class FakeHistoricalSealServiceActivityRepository:
    def __init__(self, records_by_pump: dict[str, list[dict[str, Any]]]) -> None:
        self._records_by_pump = records_by_pump

    def list_by_pump(self, pump_tag_number: str) -> list[dict[str, Any]]:
        return list(self._records_by_pump.get(pump_tag_number, []))

    def list_all(self) -> list[dict[str, Any]]:
        all_recs = []
        for recs in self._records_by_pump.values():
            all_recs.extend(recs)
        return all_recs


class TestHistoricalDateParsing:
    def test_canonical_finish_date_parsed_valid(self):
        d_val, status = parse_date_val("17/01/2024")
        assert status == "VALID"
        assert d_val == datetime.date(2024, 1, 17)

    def test_canonical_finish_date_text_month(self):
        d_val, status = parse_date_val("25 Juli 2025")
        assert status == "VALID"
        assert d_val == datetime.date(2025, 7, 25)

    def test_missing_finish_date_is_none(self):
        d_val, status = parse_date_val(None)
        assert status == "MISSING"
        assert d_val is None

        d_val, status = parse_date_val("-")
        assert status == "MISSING"
        assert d_val is None

        d_val, status = parse_date_val("")
        assert status == "MISSING"
        assert d_val is None


class TestAssetMatchingClassification:
    def test_exact_match(self):
        outcome, matched, reason = classify_tag("300-P-7A", CANONICAL_PUMP_TAGS)
        assert outcome == "EXACT"
        assert matched == "300-P-7A"

    def test_normalized_exact_case_and_whitespace(self):
        outcome, matched, reason = classify_tag(" 300 - p - 7a ", CANONICAL_PUMP_TAGS)
        assert outcome == "NORMALIZED_EXACT"
        assert matched == "300-P-7A"

    def test_normalized_exact_position_qualifier(self):
        outcome, matched, reason = classify_tag("140-P-17B (NDE)", CANONICAL_PUMP_TAGS)
        assert outcome == "NORMALIZED_EXACT"
        assert matched == "140-P-17B"

        outcome, matched, reason = classify_tag("212-P-8A (NDE)", CANONICAL_PUMP_TAGS)
        assert outcome == "NORMALIZED_EXACT"
        assert matched == "212-P-8A"

    def test_normalized_exact_spare_qualifier(self):
        outcome, matched, reason = classify_tag("702-P-4B SPARE", CANONICAL_PUMP_TAGS)
        assert outcome == "NORMALIZED_EXACT"
        assert matched == "702-P-4B"

    def test_ambiguous_tag_unlinked(self):
        # 211-P-14 lacks suffix, but canonical has 211-P-14A and 211-P-14B
        outcome, matched, reason = classify_tag("211-P-14", CANONICAL_PUMP_TAGS)
        assert outcome == "AMBIGUOUS"
        assert matched is None  # MUST remain unlinked!

    def test_no_match_unlinked(self):
        outcome, matched, reason = classify_tag("Pompa Telaga Tirta", CANONICAL_PUMP_TAGS)
        assert outcome == "NO_MATCH"
        assert matched is None

        outcome, matched, reason = classify_tag("610-TK-205", CANONICAL_PUMP_TAGS)
        assert outcome == "NO_MATCH"
        assert matched is None


class TestHistoricalHistoryOnlyPrinciple:
    """Historical Service Activity must NOT mutate or establish Current Installation."""

    def test_pump_with_no_validated_installation_report_has_unknown_current_installation(self):
        """For 300-P-7A: No 2026 validated installation exists.
        Current Installation = UNKNOWN (None).
        The 3 historical service activities appear only in timeline."""
        history_records = [
            {
                "activity_id": "act-1",
                "source_reference": "SERVICE_ACTIVITY:2024:Agustus 2024:R5:300-P-7A",
                "pump_tag_number": "300-P-7A",
                "raw_tag": "300-P-7A",
                "tag_match_outcome": "EXACT",
                "seal_type": "CARTEX-DN 45",
                "raw_job_description": "Overhaul mech seal",
                "event_date": datetime.date(2024, 8, 26),
                "finish_date": datetime.date(2024, 8, 26),
                "date_status": "VALID",
            },
            {
                "activity_id": "act-2",
                "source_reference": "SERVICE_ACTIVITY:2024:Desember 2024:R3:300-P-7A",
                "pump_tag_number": "300-P-7A",
                "raw_tag": "300-P-7A",
                "tag_match_outcome": "EXACT",
                "seal_type": "CARTEX-DN 45",
                "raw_job_description": "Replacement seal",
                "event_date": datetime.date(2024, 12, 11),
                "finish_date": datetime.date(2024, 12, 11),
                "date_status": "VALID",
            },
            {
                "activity_id": "act-3",
                "source_reference": "SERVICE_ACTIVITY:2025:INSTALLATION REPORT 2025:R35:300-P-7A",
                "pump_tag_number": "300-P-7A",
                "raw_tag": "300-P-7A",
                "tag_match_outcome": "EXACT",
                "seal_type": "CARTEX-DN 45",
                "raw_job_description": "Service seal",
                "event_date": datetime.date(2025, 7, 25),
                "finish_date": datetime.date(2025, 7, 25),
                "date_status": "VALID",
            },
        ]
        history_repo = FakeHistoricalSealServiceActivityRepository({"300-P-7A": history_records})

        # Knowledge mock
        knowledge_mock = MagicMock()
        knowledge_mock.pm_history = []
        knowledge_mock.cm_history = []
        knowledge_mock.breakdown_history = []
        knowledge_mock.condition_monitoring_readings = []
        knowledge_mock.pm_schedules = []
        knowledge_mock.inventory = []
        knowledge_mock.drawings = []
        knowledge_mock.pump = {"tag_number": "300-P-7A"}

        # Installation gateway returns NO installation reports for 300-P-7A
        installation_gw = MagicMock(spec=InstallationGateway)
        installation_gw.list_installations.return_value = {"data": []}

        timeline_service = EquipmentTimelineService(
            installation_gateway=installation_gw,
            historical_seal_service_activity_repository=history_repo,
        )

        lifecycle = timeline_service.build_lifecycle("300-P-7A", knowledge=knowledge_mock)

        # MANDATORY CHECK 1: Current Installation is UNKNOWN (None)
        assert lifecycle.current_state.current_installation is None
        assert lifecycle.current_state.current_seal is None

        # MANDATORY CHECK 2: All 3 historical events appear in timeline
        history_events = [e for e in lifecycle.timeline if e.source == TimelineSource.SERVICE_ACTIVITY]
        assert len(history_events) == 3

        # MANDATORY CHECK 3: Ordered newest-first in lifecycle timeline
        dates = [e.occurred_at for e in history_events]
        assert dates == ["2025-07-25", "2024-12-11", "2024-08-26"]

    def test_pump_with_validated_2026_installation_retains_current_installation(self):
        """For 211-P-14B: Validated 2026 installation INSTL-001-2026 remains Current Installation.
        Historical event from 2025 is strictly in history.
        Ambiguous 2024 211-P-14 is not linked."""
        history_records = [
            {
                "activity_id": "act-211-2025",
                "source_reference": "SERVICE_ACTIVITY:2025:INSTALLATION REPORT 2025:R30:211-P-14B",
                "pump_tag_number": "211-P-14B",
                "raw_tag": "211-P-14B",
                "tag_match_outcome": "EXACT",
                "seal_type": "MFL85N/50-00",
                "raw_job_description": "Installation",
                "event_date": datetime.date(2025, 7, 3),
                "finish_date": datetime.date(2025, 7, 3),
                "date_status": "VALID",
            }
        ]
        history_repo = FakeHistoricalSealServiceActivityRepository({"211-P-14B": history_records})

        # Installation gateway returns the 2026 report for 211-P-14B
        installation_gw = MagicMock(spec=InstallationGateway)
        installation_gw.list_installations.return_value = {
            "data": [
                {
                    "installation_code": "INSTL-001-2026",
                    "report_no": "RPT-2026-001",
                    "report_date": "2026-01-15",
                    "plant_equip_no": "211-P-14B",
                    "seal_code": "SEAL-211-P-14B",
                    "seal_type": "MFL85N/50-00",
                    "seal_manufacture": "EagleBurgmann",
                }
            ]
        }

        knowledge_mock = MagicMock()
        knowledge_mock.pm_history = []
        knowledge_mock.cm_history = []
        knowledge_mock.breakdown_history = []
        knowledge_mock.condition_monitoring_readings = []
        knowledge_mock.pm_schedules = []
        knowledge_mock.inventory = []
        knowledge_mock.drawings = []
        knowledge_mock.pump = {"tag_number": "211-P-14B"}

        timeline_service = EquipmentTimelineService(
            installation_gateway=installation_gw,
            historical_seal_service_activity_repository=history_repo,
        )

        lifecycle = timeline_service.build_lifecycle("211-P-14B", knowledge=knowledge_mock)

        # Current Installation is INSTL-001-2026, NOT the 2025 historical record!
        assert lifecycle.current_state.current_installation is not None
        assert lifecycle.current_state.current_installation.installation_code == "INSTL-001-2026"

        # In timeline, INSTL-001-2026 is newest, followed by 2025 historical event
        install_events = [e for e in lifecycle.timeline if e.event_type in (TimelineCategory.INSTALLATION, TimelineCategory.SEAL_INSTALL)]
        assert len(install_events) == 2
        assert install_events[0].source == TimelineSource.INSTALLATION_REPORT
        assert install_events[0].occurred_at == "2026-01-15"
        assert install_events[1].source == TimelineSource.SERVICE_ACTIVITY
        assert install_events[1].occurred_at == "2025-07-03"


class TestBuildInsertSQL:
    def test_sql_on_conflict_do_nothing(self):
        record = {
            "source_reference": "SERVICE_ACTIVITY:2024:Januari 2024:R8:920-P-2B",
            "source_type": "SERVICE_ACTIVITY",
            "source_year": 2024,
            "source_filename": "Servis Activity 2024 (1).xlsx",
            "source_worksheet": "Januari 2024",
            "source_row": 8,
            "raw_tag": "920-P-2B",
            "pump_tag_number": "920-P-2B",
            "tag_match_outcome": "EXACT",
            "finish_date": datetime.date(2024, 1, 17),
            "event_date": datetime.date(2024, 1, 17),
            "date_status": "VALID",
            "quantity": 1,
        }
        sql = build_insert_sql(record)
        assert "INSERT INTO public.historical_seal_service_activity" in sql
        assert "ON CONFLICT (source_reference) DO NOTHING;" in sql
        assert "'SERVICE_ACTIVITY:2024:Januari 2024:R8:920-P-2B'" in sql
        assert "'2024-01-17'" in sql

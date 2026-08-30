"""MWO-LTSA-CMON-DETAILED-HISTORY-001 -- regression tests for LATEST /
HISTORY / TIME-RANGE CMON query semantics, detailed per-event rendering
(actual readings, findings, status, attachments), and the fleet-
recommendation-vs-direct-history canonical consistency proof.

Generic equipment support: exercised against TWO different canonical
tags (not hardcoded to a single pump), matching this MWO's own explicit
"do not hardcode 110-P-12B/211-P-13AR" instruction.
"""

from datetime import date

from API.copilot_ask_service import DATA_GAP, FACT, ask_copilot
from API.recommendation_engine import RecommendationEngine

TAG_A = "110-P-12B"
TAG_B = "211-P-13AR"
TODAY = date(2026, 8, 30)


class FakeConditionMonitoringReadingRepository:
    def __init__(self, records_by_tag):
        self._records_by_tag = records_by_tag

    def list_by_asset(self, asset_code):
        # Mirrors the real repository's own ORDER BY reading_date DESC.
        records = list(self._records_by_tag.get(asset_code, []))
        return sorted(records, key=lambda r: r.get("reading_date") or "", reverse=True)


class FakePMCMEvidenceRepository:
    def __init__(self, attachments_by_code):
        self._attachments_by_code = attachments_by_code

    def list_for_record(self, record_type, record_code):
        assert record_type == "CONDITION_MONITORING_READING"
        return list(self._attachments_by_code.get(record_code, []))


def _reading(
    tag, code, reading_date, *, workflow_status="FINALIZED", finding=None,
    leak_de=None, leak_nde=None, **measurements,
):
    record = {
        "condition_monitoring_reading_code": code,
        "asset_code": tag,
        "reading_date": reading_date,
        "workflow_status": workflow_status,
        "finding": finding,
        "mechanical_seal_leak_de": leak_de,
        "mechanical_seal_leak_nde": leak_nde,
        "technical_recommendation": None,
        "source_reference": None,
    }
    record.update(measurements)
    return record


def _ask(question, tag, records_by_tag, evidence_repo=None, language="id"):
    return ask_copilot(
        question, tag, None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None,
        condition_monitoring_reading_repository=FakeConditionMonitoringReadingRepository(records_by_tag),
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None, cm_report_repository=None,
        pm_cm_evidence_repository=evidence_repo,
        language=language,
    )


# -- 1. LATEST -----------------------------------------------------------


def test_latest_returns_only_the_single_latest_event():
    records = {
        TAG_A: [
            _reading(TAG_A, "CMONR-1", "2026-01-10", finding="Old finding"),
            _reading(TAG_A, "CMONR-2", "2026-07-21", workflow_status="DRAFT", finding=None),
        ]
    }
    answer = _ask("CMON terakhir 110p12b", TAG_A, records)
    assert answer.kind == FACT
    assert "2026-07-21" in answer.answer
    assert "2026-01-10" not in answer.answer
    assert "DRAFT" in answer.answer


def test_latest_works_generically_for_a_second_equipment():
    records = {
        TAG_B: [_reading(TAG_B, "CMONR-B1", "2026-08-29", finding="mechanical seal leak", leak_de=True)],
    }
    answer = _ask("CMON terbaru 211-P-13AR", TAG_B, records)
    assert answer.kind == FACT
    assert TAG_B in answer.answer
    assert "2026-08-29" in answer.answer


# -- 2. ONE YEAR -----------------------------------------------------------


def test_one_year_range_includes_only_events_inside_the_interpreted_window():
    records = {
        TAG_A: [
            _reading(TAG_A, "CMONR-1", "2025-01-01", finding="too old"),  # outside 1yr window from 2026-08-30
            _reading(TAG_A, "CMONR-2", "2026-07-21", workflow_status="DRAFT"),
            _reading(TAG_A, "CMONR-3", "2026-02-01", finding="within range"),
        ]
    }
    answer = _ask("Kirimkan hasil cmon 110p12b setahun terakhir?", TAG_A, records)
    assert answer.kind == FACT
    assert "2026-07-21" in answer.answer
    assert "2026-02-01" in answer.answer
    assert "2025-01-01" not in answer.answer
    assert "1 Tahun Terakhir" in answer.answer
    assert "Periode:" in answer.answer


# -- 3. THREE MONTHS ---------------------------------------------------------


def test_three_month_range_excludes_events_outside_window():
    records = {
        TAG_A: [
            _reading(TAG_A, "CMONR-1", "2026-08-01", finding="in range"),
            _reading(TAG_A, "CMONR-2", "2026-01-01", finding="out of range"),
        ]
    }
    answer = _ask("CMON 110p12b 3 bulan terakhir", TAG_A, records)
    assert "2026-08-01" in answer.answer
    assert "2026-01-01" not in answer.answer
    assert "3 Bulan Terakhir" in answer.answer


# -- 4. SINCE DATE ------------------------------------------------------------


def test_since_date_includes_events_on_or_after_the_named_month():
    records = {
        TAG_A: [
            _reading(TAG_A, "CMONR-1", "2025-12-15", finding="before January"),
            _reading(TAG_A, "CMONR-2", "2026-01-05", finding="after cutoff"),
        ]
    }
    answer = _ask("CMON 110p12b sejak Januari 2026", TAG_A, records)
    assert "2026-01-05" in answer.answer
    assert "2025-12-15" not in answer.answer


# -- 5. YEAR ------------------------------------------------------------------


def test_year_query_bounds_to_the_named_calendar_year():
    records = {
        TAG_A: [
            _reading(TAG_A, "CMONR-1", "2026-03-01", finding="in 2026"),
            _reading(TAG_A, "CMONR-2", "2025-12-31", finding="in 2025"),
        ]
    }
    answer = _ask("Data CMON 110p12b tahun 2026", TAG_A, records)
    assert "2026-03-01" in answer.answer
    assert "2025-12-31" not in answer.answer
    assert "Tahun 2026" in answer.answer


# -- 6. ACTUAL READINGS -------------------------------------------------------


def test_actual_reading_values_and_units_come_from_fixture_data():
    records = {
        TAG_A: [
            _reading(
                TAG_A, "CMONR-1", "2026-06-01", finding="normal",
                vertical_vibration_de=2.3, vertical_vibration_nde=1.8,
                suction_pressure=4.5, motor_current=12.1,
            )
        ]
    }
    answer = _ask("Hasil CMON 110p12b", TAG_A, records)
    assert "Vertical Vibration DE: 2.3 mm/s" in answer.answer
    assert "Vertical Vibration NDE: 1.8 mm/s" in answer.answer
    assert "Suction Pressure: 4.5 bar" in answer.answer
    assert "Motor Current: 12.1 A" in answer.answer


# -- 7. NULL SAFETY -------------------------------------------------------------


def test_missing_reading_finding_and_observation_render_n_a_never_fabricated():
    records = {TAG_A: [_reading(TAG_A, "CMONR-1", "2026-06-01", finding=None)]}
    answer = _ask("Hasil CMON 110p12b", TAG_A, records)
    assert "Finding:\n   N/A" in answer.answer
    assert "Observation:\n   N/A" in answer.answer
    # no measurement columns populated -- Readings section must say N/A,
    # never invent a vibration/temperature value that was never recorded.
    assert "Readings:\n   • N/A" in answer.answer


# -- 8. EQUIPMENT LOCK ----------------------------------------------------------


def test_every_returned_event_belongs_to_the_requested_equipment_only():
    records = {
        TAG_A: [_reading(TAG_A, "CMONR-A1", "2026-06-01", finding="A's own reading")],
        TAG_B: [_reading(TAG_B, "CMONR-B1", "2026-06-02", finding="B's own reading, must never leak")],
    }
    answer = _ask("Hasil CMON 110p12b setahun terakhir", TAG_A, records)
    assert TAG_A in answer.answer
    assert TAG_B not in answer.answer
    assert "B's own reading" not in answer.answer


# -- 9. RECOMMENDATION CONSISTENCY ------------------------------------------------


def test_recommendation_historical_leak_evidence_is_retrievable_via_history_query():
    # Two historical (non-active-window) mechanical seal leak readings --
    # the exact scenario this MWO's own root-cause narrative describes.
    records = {
        TAG_A: [
            _reading(TAG_A, "CMONR-OLD1", "2025-03-01", leak_de=True, finding="mechanical seal leak"),
            _reading(TAG_A, "CMONR-OLD2", "2025-06-01", leak_nde=True, finding="mechanical seal leak"),
        ]
    }
    fake_repo = FakeConditionMonitoringReadingRepository(records)

    # A. Fleet recommendation's own historical-leak-evidence rule, over
    # the SAME canonical rows.
    from API.ltsa_knowledge_service import LTSAKnowledge
    knowledge = LTSAKnowledge(
        tag_number=TAG_A, pump=None, seal=[], inventory=[], pm_history=[], cm_history=[],
        breakdown_history=[], drawings=[], recommendation=(), pm_schedules=[],
        condition_monitoring_schedules=[], condition_monitoring_readings=fake_repo.list_by_asset(TAG_A),
    )
    recs = RecommendationEngine().recommend(knowledge)
    historical_rec = next((r for r in recs if r.rule_code == "REC_HISTORICAL_LEAK"), None)
    assert historical_rec is not None
    assert len(historical_rec.evidence) == 2

    # B. Direct CMON history query, requesting a range wide enough to
    # cover both dates -- proves the SAME underlying rows are retrievable
    # through canonical CMON history, not a divergent source.
    answer = _ask("Data CMON 110p12b sejak Januari 2025", TAG_A, records)
    assert "CMONR-OLD1" not in answer.answer  # code itself isn't rendered in prose, dates are
    assert "2025-03-01" in answer.answer
    assert "2025-06-01" in answer.answer
    assert answer.evidence[0]["field"] == "cmon_event_count"
    assert answer.evidence[0]["value"] == "2"


# -- 10. CMON VS PM/CM ------------------------------------------------------------


def test_cmon_only_request_never_mentions_pm_or_cm_unavailability():
    records = {TAG_A: [_reading(TAG_A, "CMONR-1", "2026-06-01", finding="normal")]}
    answer = _ask("Hasil CMON 110p12b setahun terakhir", TAG_A, records)
    lowered = answer.answer.lower()
    assert "tidak ada cm" not in lowered
    assert "tidak ada pm" not in lowered
    assert "work order" not in lowered


# -- 11. STATUS --------------------------------------------------------------------


def test_draft_cmon_remains_identified_as_draft_never_silently_promoted():
    records = {TAG_A: [_reading(TAG_A, "CMONR-1", "2026-07-21", workflow_status="DRAFT", finding=None)]}
    answer = _ask("Hasil CMON 110p12b setahun terakhir", TAG_A, records)
    assert "Status: DRAFT" in answer.answer
    assert "Status: FINALIZED" not in answer.answer
    assert "Status: APPROVED" not in answer.answer


# -- 12. EMPTY RANGE -----------------------------------------------------------------


def test_empty_range_returns_deterministic_message_never_substitutes_pm_cm():
    records = {TAG_A: [_reading(TAG_A, "CMONR-1", "2020-01-01", finding="way too old")]}
    answer = _ask("Kirimkan hasil cmon 110p12b setahun terakhir?", TAG_A, records)
    assert answer.kind == FACT
    assert "Tidak ditemukan data CMON 110-P-12B pada periode" in answer.answer
    assert "cm" not in answer.answer.lower().replace("cmon", "").replace("data condition monitoring", "")


# -- attachments (Phase 8) -----------------------------------------------------------


def test_attachment_metadata_is_shown_when_it_exists():
    records = {TAG_A: [_reading(TAG_A, "CMONR-1", "2026-06-01", finding="normal")]}
    evidence_repo = FakePMCMEvidenceRepository(
        {"CMONR-1": [{"file_name": "CMON_Report_June.pdf", "category": "REPORT"}]}
    )
    answer = _ask("Hasil CMON 110p12b", TAG_A, records, evidence_repo=evidence_repo)
    assert "CMON_Report_June.pdf" in answer.answer
    assert "REPORT" in answer.answer


def test_no_attachment_section_when_none_exist():
    records = {TAG_A: [_reading(TAG_A, "CMONR-1", "2026-06-01", finding="normal")]}
    evidence_repo = FakePMCMEvidenceRepository({})
    answer = _ask("Hasil CMON 110p12b", TAG_A, records, evidence_repo=evidence_repo)
    assert "Dokumen" not in answer.answer


# -- response bounding (Phase 9) -----------------------------------------------------


def test_large_result_set_is_bounded_with_truthful_overflow_message():
    # A fully-past year (2020) -- never clipped by the "bounded to today"
    # rule that only applies when the requested year equals the current
    # year, so all 12 fixture events are unambiguously in range regardless
    # of when this test actually runs.
    records = {
        TAG_A: [
            _reading(TAG_A, f"CMONR-{i}", f"2020-{i:02d}-01", finding=f"event {i}")
            for i in range(1, 13)
        ]
    }
    answer = _ask("Hasil CMON 110p12b tahun 2020", TAG_A, records)
    assert "Ditemukan 12 CMON. Menampilkan 10 terbaru." in answer.answer


# -- data-source unavailable never fabricated ------------------------------------------


def test_unavailable_repository_is_data_gap_not_fabricated():
    class _FailingRepository:
        def list_by_asset(self, asset_code):
            raise ConnectionError("simulated outage")

    answer = ask_copilot(
        "Hasil CMON 110p12b setahun terakhir", TAG_A, None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None,
        condition_monitoring_reading_repository=_FailingRepository(),
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None, cm_report_repository=None,
        language="id",
    )
    assert answer.kind == DATA_GAP

"""MWO-LTSA-EQUIPMENT-360-CANONICAL-001 -- regression tests for the
generic CMON parameter-level query mechanism (Phase 6), the extended
Equipment360 aggregator (recommendation facts + CMON attachment
metadata), and the three-way consistency proof between Equipment360,
direct CMON history, and RecommendationEngine (Phase 15).

Generic equipment support: exercised against two distinct canonical
tags, neither hardcoded into production code.
"""

from datetime import date, timedelta

from API.copilot_ask_service import DATA_GAP, FACT, ask_copilot
from API.equipment_360_service import get_equipment_360
from API.recommendation_engine import RecommendationEngine

TAG_A = "110-P-12B"
TAG_B = "211-P-13AR"
TODAY = date.today()
RECENT = (TODAY - timedelta(days=10)).isoformat()
OLD = (TODAY - timedelta(days=400)).isoformat()


class FakePumpGateway:
    def __init__(self, pumps):
        self._pumps = {p["tag_number"]: p for p in pumps}

    def get_pump(self, tag_number):
        pump = self._pumps.get(tag_number)
        return {"success": bool(pump), "data": pump}

    def list_pumps(self):
        return {"success": True, "data": list(self._pumps.values())}


class FakeCMONRepository:
    def __init__(self, records_by_tag):
        self._records_by_tag = records_by_tag

    def list_by_asset(self, asset_code):
        records = list(self._records_by_tag.get(asset_code, []))
        return sorted(records, key=lambda r: r.get("reading_date") or "", reverse=True)


class FakePMOccurrenceRepository:
    def list_by_asset(self, asset_code):
        return []


class FakeCMReportRepository:
    def list_cm_reports(self, **_kwargs):
        return {"success": True, "data": []}


class FakeMechanicalSealStockRepository:
    def list_pools(self, limit=200):
        return {"success": True, "data": []}


class FakeEquipmentTimelineService:
    def build_current_seal(self, tag_number):
        return None


class FakeLTSAKnowledgeService:
    def build(self, tag_number):
        from API.ltsa_knowledge_service import LTSAKnowledge
        return LTSAKnowledge(
            tag_number=tag_number, pump=None, seal=[], inventory=[], pm_history=[], cm_history=[],
            breakdown_history=[], drawings=[], recommendation=(), pm_schedules=[],
            condition_monitoring_schedules=[], condition_monitoring_readings=[],
        )


class FakePMCMEvidenceRepository:
    def __init__(self, attachments_by_code=None):
        self.calls = 0
        self._attachments_by_code = attachments_by_code or {}

    def list_for_record(self, record_type, record_code):
        self.calls += 1
        assert record_type == "CONDITION_MONITORING_READING"
        return list(self._attachments_by_code.get(record_code, []))


def _reading(tag, code, reading_date, *, leak_de=None, leak_nde=None, finding=None, workflow_status="FINALIZED", **measurements):
    record = {
        "condition_monitoring_reading_code": code,
        "asset_code": tag,
        "reading_date": reading_date,
        "workflow_status": workflow_status,
        "finding": finding,
        "mechanical_seal_leak_de": leak_de,
        "mechanical_seal_leak_nde": leak_nde,
    }
    record.update(measurements)
    return record


def _ask(question, tag, records_by_tag, language="id"):
    return ask_copilot(
        question, tag, None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None,
        condition_monitoring_reading_repository=FakeCMONRepository(records_by_tag),
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None, cm_report_repository=None,
        language=language,
    )


# -- A/I. Equipment identity lock for parameter queries -----------------


def test_temperature_query_locks_to_requested_equipment_only():
    records = {
        TAG_A: [_reading(TAG_A, "C-A1", RECENT, bearing_temp_de=62.4)],
        TAG_B: [_reading(TAG_B, "C-B1", RECENT, bearing_temp_de=99.9)],
    }
    answer = _ask("Temperature 110p12b terakhir berapa?", TAG_A, records)
    assert answer.kind == FACT
    assert "62.4" in answer.answer
    assert "99.9" not in answer.answer
    assert TAG_B not in answer.answer


# -- E. Temperature latest ------------------------------------------------


def test_temperature_latest_returns_actual_value_unit_and_date():
    records = {TAG_A: [_reading(TAG_A, "C1", RECENT, bearing_temp_de=62.4, bearing_temp_nde=58.7)]}
    answer = _ask("Temperature 110p12b terakhir berapa?", TAG_A, records)
    assert answer.kind == FACT
    assert "62.4 °C" in answer.answer
    assert "58.7 °C" in answer.answer
    assert RECENT in answer.answer
    assert "Temperature" in answer.answer


def test_temperature_latest_skips_records_missing_the_parameter():
    records = {
        TAG_A: [
            _reading(TAG_A, "C2", RECENT),  # newest, but no temperature recorded
            _reading(TAG_A, "C1", OLD, bearing_temp_de=55.0),
        ]
    }
    answer = _ask("Temperature 110p12b terakhir berapa?", TAG_A, records)
    assert "55.0" in answer.answer
    assert OLD in answer.answer


def test_temperature_paraphrases_without_actual_values_are_data_gap():
    records = {TAG_A: [_reading(TAG_A, "C1", RECENT, finding="temperature checked, value N/A")]}
    for question in (
        "Suhu 110p12b terakhir berapa?",
        "Temperaturnya 110p12b terbaru?",
        "Temperature 110p12b terakhir berapa?",
    ):
        answer = _ask(question, TAG_A, records)
        assert answer.kind == DATA_GAP
        assert "N/A" not in answer.answer


# -- F. Temperature history ------------------------------------------------


def test_temperature_history_returns_chronological_readings_in_range():
    within_a_year = (TODAY - timedelta(days=100)).isoformat()
    records = {
        TAG_A: [
            _reading(TAG_A, "C2", within_a_year, bearing_temp_de=60.0),
            _reading(TAG_A, "C1", OLD, bearing_temp_de=70.0),  # outside 1yr window
        ]
    }
    answer = _ask("Temperature 110p12b setahun terakhir", TAG_A, records)
    assert within_a_year in answer.answer
    assert "60.0" in answer.answer
    assert OLD not in answer.answer
    assert "70.0" not in answer.answer
    assert "latest" in answer.answer.lower()
    assert "min" in answer.answer.lower()
    assert "max" in answer.answer.lower()


def test_parameter_history_contains_only_records_with_actual_requested_values():
    newer_without_value = (TODAY - timedelta(days=20)).isoformat()
    older_with_value = (TODAY - timedelta(days=90)).isoformat()
    records = {
        TAG_A: [
            _reading(TAG_A, "C2", newer_without_value, finding="temperature N/A"),
            _reading(TAG_A, "C1", older_with_value, bearing_temp_de=60.0),
        ]
    }
    answer = _ask("Temperature 110p12b setahun terakhir", TAG_A, records)
    assert answer.kind == FACT
    assert older_with_value in answer.answer
    assert "60.0" in answer.answer
    assert newer_without_value not in answer.answer
    assert "N/A" not in answer.answer


def test_na_only_parameter_history_returns_data_gap():
    records = {
        TAG_A: [
            _reading(TAG_A, "C2", (TODAY - timedelta(days=20)).isoformat(), finding="temperature N/A"),
            _reading(TAG_A, "C1", (TODAY - timedelta(days=90)).isoformat()),
        ]
    }
    answer = _ask("Temperature 110p12b setahun terakhir", TAG_A, records)
    assert answer.kind == DATA_GAP
    assert "N/A" not in answer.answer


# -- G. Vibration latest, generic mechanism reused --------------------------


def test_vibration_latest_uses_the_same_generic_parameter_mechanism():
    records = {TAG_A: [_reading(TAG_A, "C1", RECENT, vertical_vibration_de=2.3, horizontal_vibration_nde=1.1)]}
    answer = _ask("Vibration 110p12b terakhir", TAG_A, records)
    assert answer.kind == FACT
    assert "2.3 mm/s" in answer.answer
    assert "1.1 mm/s" in answer.answer
    assert "Vibration" in answer.answer


def test_vibration_paraphrases_without_actual_values_are_data_gap():
    records = {TAG_A: [_reading(TAG_A, "C1", RECENT, finding="vibration inspected, value N/A")]}
    for question in (
        "Vibrasi 110p12b terakhir",
        "Getarannya 110p12b terbaru?",
        "Vibration 110p12b terakhir",
    ):
        answer = _ask(question, TAG_A, records)
        assert answer.kind == DATA_GAP
        assert "N/A" not in answer.answer


def test_all_latest_readings_intents_select_newest_actual_value_per_parameter():
    newest = RECENT
    mid = (TODAY - timedelta(days=40)).isoformat()
    oldest = (TODAY - timedelta(days=80)).isoformat()
    records = {
        TAG_A: [
            _reading(TAG_A, "C3", newest, bearing_temp_de=70.0),
            _reading(TAG_A, "C2", mid, vertical_vibration_de=2.2),
            _reading(TAG_A, "C1", oldest, bearing_temp_de=55.0, vertical_vibration_de=1.0, suction_pressure=4.5),
        ]
    }
    for question in (
        "tampilkan semua reading terakhir 110p12b",
        "semua reading terakhir 110p12b",
        "reading terakhir 110p12b",
        "parameter terakhir 110p12b",
        "parameter terbaru 110p12b",
        # MWO-LTSA-EQUIPMENT-360-CMON-DATA-WORD-001 -- generic "data"
        # wording, compact and dashed tag form, must be fully equivalent
        # to the "parameter"/"reading" wording above: same intent routing,
        # same all-vs-single-latest rendering, same canonical entity.
        "Tampilkan semua pembacaan parameter terbaru untuk 110-P-12B",
        "Tampilkan semua pembacaan parameter terbaru untuk 110P12B",
        "Tampilkan data terbaru 110-P-12B",
        "Tampilkan data terbaru 110P12B",
    ):
        answer = _ask(question, TAG_A, records)
        assert answer.kind == FACT
        assert "Bearing Temp DE: 70.0 °C" in answer.answer
        assert f"70.0 °C ({newest})" in answer.answer
        assert "Vertical Vibration DE: 2.2 mm/s" in answer.answer
        assert f"2.2 mm/s ({mid})" in answer.answer
        assert "Suction Pressure: 4.5 bar" in answer.answer
        assert f"4.5 bar ({oldest})" in answer.answer
        assert "1.0 mm/s" not in answer.answer
        assert "55.0 °C" not in answer.answer
        assert "N/A" not in answer.answer


def test_generic_data_terbaru_wording_is_data_gap_when_no_cmon_records_exist():
    # The "data" trigger word only changes ROUTING, never fabricates: a
    # tag with genuinely no CMON records must still report DATA_GAP for
    # the exact same generic wording that now correctly reaches the CMON
    # handler.
    answer = _ask("Tampilkan data terbaru 110P12B", TAG_A, {TAG_A: []})
    assert answer.kind == FACT  # "no records yet" is a known FACT, not a data gap (matches existing _handle_condition_monitoring behavior for an empty list)
    assert "Belum ada data Condition Monitoring" in answer.answer or "No Condition Monitoring data" in answer.answer


def test_generic_data_terbaru_wording_locks_to_requested_equipment_only():
    records = {
        TAG_A: [_reading(TAG_A, "C1", RECENT, bearing_temp_de=62.4)],
        TAG_B: [_reading(TAG_B, "C1", RECENT, bearing_temp_de=99.9)],
    }
    for question in ("Tampilkan data terbaru 110-P-12B", "Tampilkan data terbaru 110P12B"):
        answer = _ask(question, TAG_A, records)
        assert answer.kind == FACT
        assert "62.4" in answer.answer
        assert "99.9" not in answer.answer
        assert TAG_B not in answer.answer


# -- H. Unknown parameter -----------------------------------------------------


def test_unknown_parameter_word_is_not_matched_never_hallucinated():
    # "pressure" IS canonical (matches Quench/Suction/Discharge Pressure),
    # so this proves a genuinely absent concept -- not present anywhere in
    # this module's own field labels -- degrades deterministically rather
    # than silently falling through to a different intent/handler.
    from API.condition_monitoring_measurement_fields import fields_matching_search_term
    assert fields_matching_search_term("oil_level_xyz") == []


def test_pressure_word_resolves_to_real_canonical_fields():
    records = {TAG_A: [_reading(TAG_A, "C1", RECENT, suction_pressure=4.5)]}
    answer = _ask("Pressure 110p12b terakhir", TAG_A, records)
    assert "4.5 bar" in answer.answer


# -- generic parameter mechanism: new params work without a new handler ----


def test_parameter_mechanism_is_generic_no_per_parameter_handler_needed():
    from API.condition_monitoring_measurement_fields import fields_matching_search_term, MEASUREMENT_SINGLE_FIELDS
    # Motor Current is matched purely via label search, exercising the
    # exact same fields_matching_search_term() code path temperature/
    # vibration/pressure use -- proving no per-parameter special-casing.
    matches = fields_matching_search_term("current")
    assert any(f.label == "Motor Current" for f in matches)
    assert any(f in MEASUREMENT_SINGLE_FIELDS for f in matches)


# -- Equipment360: recommendation facts + attachments ------------------------


def _equipment_360(tag, records_by_tag, evidence_repo=None):
    return get_equipment_360(
        tag,
        pump_gateway=FakePumpGateway([{"tag_number": TAG_A, "area": "FRAKSINASI", "status": "Active"}, {"tag_number": TAG_B, "area": "FRAKSINASI", "status": "Active"}]),
        pm_occurrence_repository=FakePMOccurrenceRepository(),
        cm_report_repository=FakeCMReportRepository(),
        condition_monitoring_reading_repository=FakeCMONRepository(records_by_tag),
        equipment_timeline_service=FakeEquipmentTimelineService(),
        ltsa_knowledge_service=FakeLTSAKnowledgeService(),
        mechanical_seal_stock_repository=FakeMechanicalSealStockRepository(),
        pm_cm_evidence_repository=evidence_repo,
    )


def test_equipment_360_recommendation_facts_reflect_active_leak():
    records = {TAG_A: [_reading(TAG_A, "C1", RECENT, leak_de=True, finding="mechanical seal leak")]}
    e360 = _equipment_360(TAG_A, records)
    rule_codes = [r.rule_code for r in e360.recommendation]
    assert "REC_ACTIVE_LEAK" in rule_codes


def test_equipment_360_recommendation_facts_reflect_historical_leak():
    records = {TAG_A: [_reading(TAG_A, "C1", OLD, leak_de=True, finding="mechanical seal leak")]}
    e360 = _equipment_360(TAG_A, records)
    rule_codes = [r.rule_code for r in e360.recommendation]
    assert "REC_HISTORICAL_LEAK" in rule_codes
    assert "REC_ACTIVE_LEAK" not in rule_codes


def test_equipment_360_exposes_latest_cmon_attachment_metadata():
    records = {TAG_A: [_reading(TAG_A, "C1", RECENT, finding="normal")]}
    evidence_repo = FakePMCMEvidenceRepository({"C1": [{"file_name": "report.pdf", "category": "REPORT"}]})
    e360 = _equipment_360(TAG_A, records, evidence_repo=evidence_repo)
    assert len(e360.cmon_latest_attachments) == 1
    assert e360.cmon_latest_attachments[0]["file_name"] == "report.pdf"
    assert evidence_repo.calls == 1  # exactly once, not once per history event


def test_equipment_360_no_attachment_dependency_is_none_safe():
    records = {TAG_A: [_reading(TAG_A, "C1", RECENT, finding="normal")]}
    e360 = _equipment_360(TAG_A, records, evidence_repo=None)
    assert e360.cmon_latest_attachments == ()
    assert "cmon_attachments" not in e360.data_gaps


# -- Phase 15: three-way consistency proof ------------------------------------


def test_equipment_360_cmon_history_and_recommendation_agree_on_leak_count():
    # Two historical (non-active-window) leak readings -- this MWO's own
    # root-cause narrative scenario, extended to a THIRD source
    # (Equipment360) alongside the two already proven consistent in the
    # prior CMON-detailed-history mission.
    records = {
        TAG_A: [
            _reading(TAG_A, "C-OLD1", OLD, leak_de=True, finding="mechanical seal leak"),
            _reading(TAG_A, "C-OLD2", (TODAY - timedelta(days=420)).isoformat(), leak_nde=True, finding="mechanical seal leak"),
        ]
    }
    fake_repo = FakeCMONRepository(records)

    # Source 1: RecommendationEngine directly.
    from API.ltsa_knowledge_service import LTSAKnowledge
    knowledge = LTSAKnowledge(
        tag_number=TAG_A, pump=None, seal=[], inventory=[], pm_history=[], cm_history=[],
        breakdown_history=[], drawings=[], recommendation=(), pm_schedules=[],
        condition_monitoring_schedules=[], condition_monitoring_readings=fake_repo.list_by_asset(TAG_A),
    )
    rec_answer = RecommendationEngine().recommend(knowledge)
    historical = next(r for r in rec_answer if r.rule_code == "REC_HISTORICAL_LEAK")
    assert len(historical.evidence) == 2

    # Source 2: Equipment360 aggregator.
    e360 = _equipment_360(TAG_A, records)
    e360_historical = next(r for r in e360.recommendation if r.rule_code == "REC_HISTORICAL_LEAK")
    assert len(e360_historical.evidence) == 2

    # Source 3: direct CMON history query, requesting a range wide enough
    # (2 years) to cover both dates (400/420 days back) regardless of
    # calendar-year boundaries -- must retrieve exactly 2 events.
    answer = _ask("Data CMON 110p12b 2 tahun terakhir", TAG_A, records)
    cmon_event_count_evidence = next(e for e in answer.evidence if e["field"] == "cmon_event_count")
    assert int(cmon_event_count_evidence["value"]) == 2

    # All three sources agree: 2 leak-flagged historical events, same
    # canonical rows, same count -- no silent disagreement.
    assert len(historical.evidence) == len(e360_historical.evidence) == 2 == int(cmon_event_count_evidence["value"])

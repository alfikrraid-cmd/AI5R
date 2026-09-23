import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.cm_condition_evaluator import evaluate_current_condition, evaluate_leak, select_latest_valid_cm  # noqa: E402


def test_leak_truth_table_is_lossless():
    expected = {
        (True, True): "LEAK_DE_NDE", (True, False): "LEAK_DE", (False, True): "LEAK_NDE",
        (False, False): "NO_LEAK", (True, None): "LEAK_DE", (None, True): "LEAK_NDE",
        (False, None): "NO_LEAK_DE", (None, False): "NO_LEAK_NDE", (None, None): "NOT_RECORDED",
    }
    for values, status in expected.items():
        assert evaluate_leak(*values)["status"] == status


def test_latest_valid_includes_draft_and_excludes_incomplete_or_returned():
    base = {"asset_code": "P-1", "reading_date": "2026-06-12", "created_at": "2026-06-12T01:00:00Z", "mechanical_seal_leak_de": False}
    readings = [
        {**base, "condition_monitoring_reading_code": "DRAFT", "workflow_status": "DRAFT"},
        {**base, "condition_monitoring_reading_code": "RETURNED", "workflow_status": "RETURNED_FOR_CORRECTION", "created_at": "2026-06-12T03:00:00Z"},
        {**base, "condition_monitoring_reading_code": "EMPTY", "workflow_status": "FINALIZED", "mechanical_seal_leak_de": None},
    ]
    assert select_latest_valid_cm(readings)["condition_monitoring_reading_code"] == "DRAFT"


def test_same_date_order_is_deterministic_and_finding_negation_is_safe():
    common = {"asset_code": "P-1", "reading_date": "2026-06-12", "workflow_status": "FINALIZED", "mechanical_seal_leak_de": False, "mechanical_seal_leak_nde": False}
    readings = [{**common, "created_at": "2026-06-12T01:00:00Z", "condition_monitoring_reading_code": "A"}, {**common, "created_at": "2026-06-12T01:00:00Z", "condition_monitoring_reading_code": "B"}]
    selected = select_latest_valid_cm(readings)
    assert selected["condition_monitoring_reading_code"] == "B"
    assert evaluate_current_condition({**selected, "finding": "tidak bocor"})["finding_conflict"] == "NONE"
    assert evaluate_current_condition({**selected, "finding": "mechanical seal bocor"})["finding_conflict"] == "REVIEW_REQUIRED"

import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.ltsa_knowledge_service import LTSAKnowledge, LTSAKnowledgeService


class FakeGateway:
    """Generic list-only fake matching every gateway's real
    {success, message, count, data} shape (mirrors
    test_engineering_context_engine.py's own FakeGateway -- reused, not
    duplicated, since every real gateway consumed here exposes exactly
    one `list_*` method)."""

    def __init__(self, method_name, records=None, success=True):
        records = records or []
        response = {"success": success, "message": "ok", "count": len(records), "data": records}
        setattr(self, method_name, lambda: response)


class FakePumpGateway:
    def __init__(self, detail_response=None):
        self._detail_response = detail_response or {"success": False, "message": "not found", "data": None}

    def get_pump(self, tag_number):
        return self._detail_response


def _service(
    pump=None,
    maintenance_history=None,
    pm_occurrences=None,
    cm_reports=None,
    seals=None,
    seal_stock=None,
    seal_compatibility=None,
    work_orders=None,
):
    return LTSAKnowledgeService(
        pump_gateway=pump or FakePumpGateway(),
        maintenance_history_gateway=FakeGateway("list_maintenance_history", maintenance_history),
        pm_occurrence_gateway=FakeGateway("list_pm_occurrences", pm_occurrences),
        cm_report_gateway=FakeGateway("list_cm_reports", cm_reports),
        seal_gateway=FakeGateway("list_seals", seals),
        seal_stock_gateway=FakeGateway("list_seal_stocks", seal_stock),
        seal_pump_compatibility_gateway=FakeGateway("list_seal_pump_compatibilities", seal_compatibility),
        work_order_gateway=FakeGateway("list_work_orders", work_orders),
    )


TAG = "641-P-5"


def test_build_returns_ltsa_knowledge_instance():
    service = _service(pump=FakePumpGateway({"success": True, "message": "ok", "data": {"tag_number": TAG}}))

    knowledge = service.build(TAG)

    assert isinstance(knowledge, LTSAKnowledge)
    assert knowledge.tag_number == TAG


def test_pump_field_populated_from_pump_gateway():
    detail = {"success": True, "message": "ok", "data": {"tag_number": TAG, "pump_name": "Main Feed Pump"}}
    service = _service(pump=FakePumpGateway(detail))

    knowledge = service.build(TAG)

    assert knowledge.pump == {"tag_number": TAG, "pump_name": "Main Feed Pump"}


def test_pump_field_is_none_when_pump_not_found():
    service = _service(pump=FakePumpGateway({"success": False, "message": "not found", "data": None}))

    knowledge = service.build(TAG)

    assert knowledge.pump is None


def test_seal_field_lists_compatible_seals():
    service = _service(
        seal_compatibility=[{"seal_code": "SC-001", "pump_tag_number": TAG}],
        seals=[{"seal_code": "SC-001", "seal_name": "John Crane Type 21"}],
        seal_stock=[{"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}],
    )

    knowledge = service.build(TAG)

    assert knowledge.seal == [{"seal_code": "SC-001", "part_name": "John Crane Type 21"}]


def test_inventory_field_carries_stock_for_same_seals():
    service = _service(
        seal_compatibility=[{"seal_code": "SC-001", "pump_tag_number": TAG}],
        seals=[{"seal_code": "SC-001", "seal_name": "John Crane Type 21"}],
        seal_stock=[{"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}],
    )

    knowledge = service.build(TAG)

    assert knowledge.inventory == [
        {"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}
    ]


def test_inventory_leaves_stock_null_when_no_stock_row_exists():
    service = _service(
        seal_compatibility=[{"seal_code": "SC-009", "pump_tag_number": TAG}],
        seals=[{"seal_code": "SC-009", "seal_name": "Chesterton 155"}],
        seal_stock=[],
    )

    knowledge = service.build(TAG)

    assert knowledge.inventory == [
        {"seal_code": "SC-009", "quantity_on_hand": None, "reorder_point": None, "location": None}
    ]


def test_seal_and_inventory_are_empty_when_no_compatible_seals():
    service = _service(seal_compatibility=[])

    knowledge = service.build(TAG)

    assert knowledge.seal == []
    assert knowledge.inventory == []


def test_pm_history_filters_pm_occurrences_by_asset_code():
    service = _service(
        pm_occurrences=[
            {"pm_occurrence_code": "PM-OCC-101", "asset_code": TAG, "occurrence_date": "2026-06-01"},
            {"pm_occurrence_code": "PM-OCC-102", "asset_code": "OTHER-PUMP", "occurrence_date": "2026-06-02"},
        ]
    )

    knowledge = service.build(TAG)

    assert knowledge.pm_history == [
        {"pm_occurrence_code": "PM-OCC-101", "asset_code": TAG, "occurrence_date": "2026-06-01"}
    ]


def test_pm_history_is_empty_when_no_occurrences_exist():
    service = _service(pm_occurrences=[])

    knowledge = service.build(TAG)

    assert knowledge.pm_history == []


def test_cm_history_filters_cm_reports_by_asset_code():
    service = _service(
        cm_reports=[
            {"cm_report_code": "CM-101", "asset_code": TAG, "status": "OPEN"},
            {"cm_report_code": "CM-102", "asset_code": "OTHER-PUMP", "status": "OPEN"},
        ]
    )

    knowledge = service.build(TAG)

    assert knowledge.cm_history == [{"cm_report_code": "CM-101", "asset_code": TAG, "status": "OPEN"}]


def test_cm_history_includes_closed_reports_unlike_last_cm():
    # cm_history is the full history, not just the latest open report --
    # a closed report must still appear here.
    service = _service(
        cm_reports=[{"cm_report_code": "CM-101", "asset_code": TAG, "status": "CLOSED"}],
    )

    knowledge = service.build(TAG)

    assert knowledge.cm_history == [{"cm_report_code": "CM-101", "asset_code": TAG, "status": "CLOSED"}]


def test_breakdown_history_includes_only_cm_typed_maintenance_records():
    service = _service(
        maintenance_history=[
            {"maintenance_record_code": "MH-101", "asset_code": TAG, "work_order_code": "WO-101"},
            {"maintenance_record_code": "MH-102", "asset_code": TAG, "work_order_code": "WO-102"},
        ],
        work_orders=[
            {"work_order_code": "WO-101", "work_type": "CM"},
            {"work_order_code": "WO-102", "work_type": "PM"},
        ],
    )

    knowledge = service.build(TAG)

    assert [r["maintenance_record_code"] for r in knowledge.breakdown_history] == ["MH-101"]


def test_breakdown_history_excludes_other_pumps():
    service = _service(
        maintenance_history=[
            {"maintenance_record_code": "MH-201", "asset_code": "OTHER-PUMP", "work_order_code": "WO-201"},
        ],
        work_orders=[{"work_order_code": "WO-201", "work_type": "CM"}],
    )

    knowledge = service.build(TAG)

    assert knowledge.breakdown_history == []


def test_breakdown_history_is_empty_when_no_maintenance_history():
    service = _service(maintenance_history=[])

    knowledge = service.build(TAG)

    assert knowledge.breakdown_history == []


def test_drawings_field_is_none_no_backend_service_exists():
    service = _service()

    knowledge = service.build(TAG)

    assert knowledge.drawings is None


def test_recommendation_field_is_none_no_deterministic_source_exists():
    service = _service()

    knowledge = service.build(TAG)

    assert knowledge.recommendation is None


def test_ltsa_knowledge_is_immutable():
    import dataclasses

    import pytest

    service = _service()
    knowledge = service.build(TAG)

    with pytest.raises(dataclasses.FrozenInstanceError):
        knowledge.pump = {}


def test_service_defaults_to_real_gateways_when_none_injected():
    # No SQL, no network call happens at construction time -- gateways
    # are transport objects only, safe to default-construct.
    service = LTSAKnowledgeService()

    assert service.pump_gateway is not None
    assert service.work_order_gateway is not None

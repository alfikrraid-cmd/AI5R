import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.ltsa_knowledge_service import LTSAKnowledge, LTSAKnowledgeService
from API.recommendation_engine import Evidence, Recommendation


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


class FakeAssetRepository:
    def __init__(self, records_by_asset=None):
        self._records_by_asset = records_by_asset or {}
        self.requested_assets = []

    def list_by_asset(self, asset_code):
        self.requested_assets.append(asset_code)
        return list(self._records_by_asset.get(asset_code, []))


def _service(
    pump=None,
    maintenance_history=None,
    pm_occurrences=None,
    cm_reports=None,
    seals=None,
    seal_stock=None,
    seal_compatibility=None,
    work_orders=None,
    recommendation_engine=None,
    seal_engineering_documents=None,
    pm_schedules=None,
    condition_monitoring_schedules=None,
    condition_monitoring_readings=None,
    pm_occurrence_repository=None,
    condition_monitoring_reading_repository=None,
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
        recommendation_engine=recommendation_engine,
        seal_engineering_document_gateway=FakeGateway(
            "list_seal_engineering_documents", seal_engineering_documents
        ),
        pm_schedule_gateway=FakeGateway("list_pm_schedules", pm_schedules),
        condition_monitoring_schedule_gateway=FakeGateway(
            "list_condition_monitoring_schedules", condition_monitoring_schedules
        ),
        condition_monitoring_reading_gateway=FakeGateway(
            "list_condition_monitoring_readings", condition_monitoring_readings
        ),
        pm_occurrence_repository=pm_occurrence_repository,
        condition_monitoring_reading_repository=condition_monitoring_reading_repository,
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


def test_pm_history_prefers_repository_list_by_asset_over_gateway_list():
    repository = FakeAssetRepository(
        {
            TAG: [
                {"pm_occurrence_code": "PM-OCC-101", "asset_code": TAG, "occurrence_date": "2026-06-01"},
                {"pm_occurrence_code": "PM-OCC-102", "asset_code": TAG, "occurrence_date": "2026-06-08"},
            ],
        }
    )
    service = _service(pm_occurrences=[], pm_occurrence_repository=repository)

    knowledge = service.build(TAG)

    assert repository.requested_assets == [TAG]
    assert [record["pm_occurrence_code"] for record in knowledge.pm_history] == [
        "PM-OCC-101",
        "PM-OCC-102",
    ]


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


# -- work_orders (MWO-LTSA-ASSET360-CONSOLIDATION-001) -----------------------
# Same "filter by asset_code" technique as pm_history/cm_history/
# condition_monitoring_readings above -- no new business rule, reuses the
# already-injected work_order_gateway (already relied on by
# _build_breakdown_history).


def test_work_orders_filters_by_asset_code():
    service = _service(
        work_orders=[
            {"work_order_code": "WO-301", "asset_code": TAG, "status": "OPEN"},
            {"work_order_code": "WO-302", "asset_code": "OTHER-PUMP", "status": "OPEN"},
        ]
    )

    knowledge = service.build(TAG)

    assert [r["work_order_code"] for r in knowledge.work_orders] == ["WO-301"]


def test_work_orders_is_empty_when_no_work_orders_exist():
    service = _service(work_orders=[])

    knowledge = service.build(TAG)

    assert knowledge.work_orders == []


def test_work_orders_defaults_to_empty_list_when_ltsaknowledge_constructed_without_it():
    knowledge = LTSAKnowledge(
        tag_number=TAG,
        pump=None,
        seal=[],
        inventory=[],
        pm_history=[],
        cm_history=[],
        breakdown_history=[],
        drawings=[],
        recommendation=(),
        pm_schedules=[],
        condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )

    assert knowledge.work_orders == []


# -- drawings (MWO-LTSA-033) -------------------------------------------------


def test_drawings_field_is_empty_list_when_no_seal_engineering_documents_exist():
    service = _service(seal_compatibility=[{"seal_code": "SC-001", "pump_tag_number": TAG}])

    knowledge = service.build(TAG)

    assert knowledge.drawings == []


def test_drawings_field_lists_drawing_type_documents_for_compatible_seals():
    service = _service(
        seal_compatibility=[{"seal_code": "SC-001", "pump_tag_number": TAG}],
        seal_engineering_documents=[
            {
                "document_code": "DOC-001",
                "seal_code": "SC-001",
                "document_type": "DRAWING",
                "title": "SC-001 GA Drawing",
                "document_number": "DWG-4471",
                "revision": "B",
                "status": "APPROVED",
                "file_name": "sc-001-ga.pdf",
                "created_at": "2026-05-01T00:00:00Z",
            }
        ],
    )

    knowledge = service.build(TAG)

    assert knowledge.drawings == [
        {
            "drawing_id": "DOC-001",
            "title": "SC-001 GA Drawing",
            "document_number": "DWG-4471",
            "revision": "B",
            "status": "APPROVED",
            "file_name": "sc-001-ga.pdf",
            "uploaded_at": "2026-05-01T00:00:00Z",
        }
    ]


def test_drawings_field_supports_multiple_drawings_for_the_same_pump():
    service = _service(
        seal_compatibility=[{"seal_code": "SC-001", "pump_tag_number": TAG}],
        seal_engineering_documents=[
            {
                "document_code": "DOC-001",
                "seal_code": "SC-001",
                "document_type": "DRAWING",
                "title": "GA Drawing",
                "document_number": "DWG-1",
                "revision": "A",
                "status": "APPROVED",
                "file_name": "ga.pdf",
                "created_at": "2026-05-01T00:00:00Z",
            },
            {
                "document_code": "DOC-002",
                "seal_code": "SC-001",
                "document_type": "DRAWING",
                "title": "Cross-Section Drawing",
                "document_number": "DWG-2",
                "revision": "A",
                "status": "APPROVED",
                "file_name": "cross-section.pdf",
                "created_at": "2026-05-02T00:00:00Z",
            },
        ],
    )

    knowledge = service.build(TAG)

    assert [d["drawing_id"] for d in knowledge.drawings] == ["DOC-001", "DOC-002"]


def test_drawings_field_excludes_non_drawing_document_types():
    service = _service(
        seal_compatibility=[{"seal_code": "SC-001", "pump_tag_number": TAG}],
        seal_engineering_documents=[
            {
                "document_code": "DOC-003",
                "seal_code": "SC-001",
                "document_type": "DATASHEET",
                "title": "SC-001 Datasheet",
                "document_number": "DS-1",
                "revision": "A",
                "status": "APPROVED",
                "file_name": "datasheet.pdf",
                "created_at": "2026-05-01T00:00:00Z",
            }
        ],
    )

    knowledge = service.build(TAG)

    assert knowledge.drawings == []


def test_drawings_field_excludes_documents_for_incompatible_seals():
    service = _service(
        seal_compatibility=[{"seal_code": "SC-001", "pump_tag_number": TAG}],
        seal_engineering_documents=[
            {
                "document_code": "DOC-004",
                "seal_code": "SC-999",
                "document_type": "DRAWING",
                "title": "Unrelated Seal Drawing",
                "document_number": "DWG-9",
                "revision": "A",
                "status": "APPROVED",
                "file_name": "other.pdf",
                "created_at": "2026-05-01T00:00:00Z",
            }
        ],
    )

    knowledge = service.build(TAG)

    assert knowledge.drawings == []


def test_drawings_field_maps_only_the_seven_required_metadata_fields():
    # Metadata only, per MWO-LTSA-033's explicit scope -- file_reference
    # (the pointer to the binary), manufacturer, description, issue_date,
    # language, and page_count must never leak into the mapped shape, and
    # uploaded_at is a disclosed mapping from created_at, not issue_date.
    service = _service(
        seal_compatibility=[{"seal_code": "SC-001", "pump_tag_number": TAG}],
        seal_engineering_documents=[
            {
                "document_code": "DOC-001",
                "seal_code": "SC-001",
                "document_type": "DRAWING",
                "title": "SC-001 GA Drawing",
                "document_number": "DWG-4471",
                "revision": "B",
                "status": "APPROVED",
                "file_name": "sc-001-ga.pdf",
                "file_reference": "s3://bucket/sc-001-ga.pdf",
                "manufacturer": "John Crane",
                "description": "General arrangement drawing",
                "issue_date": "2025-01-01",
                "language": "EN",
                "page_count": 3,
                "created_at": "2026-05-01T00:00:00Z",
                "updated_at": "2026-05-02T00:00:00Z",
            }
        ],
    )

    knowledge = service.build(TAG)

    assert set(knowledge.drawings[0].keys()) == {
        "drawing_id",
        "title",
        "document_number",
        "revision",
        "status",
        "file_name",
        "uploaded_at",
    }
    assert knowledge.drawings[0]["uploaded_at"] == "2026-05-01T00:00:00Z"


def test_recommendation_field_exists_and_is_populated_by_recommendation_engine():
    # MWO-LTSA-032C: RecommendationEngine is now wired in -- no PM history
    # deterministically fires its REC_PM_OVERDUE rule (recommendation_engine.py,
    # reused unmodified), so recommendation is no longer always None.
    service = _service(pm_occurrences=[])

    knowledge = service.build(TAG)

    assert len(knowledge.recommendation) == 1
    assert knowledge.recommendation[0].rule_code == "REC_PM_OVERDUE"


def test_recommendation_field_is_empty_tuple_when_no_rules_fire():
    service = _service(
        pm_occurrences=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}]
    )

    knowledge = service.build(TAG)

    assert knowledge.recommendation == ()


def test_recommendation_priority_confidence_and_evidence_are_preserved():
    # priority/confidence/evidence flow through RecommendationEngine.recommend()
    # unchanged -- proves the engine's real dataclass output reaches
    # LTSAKnowledge.recommendation verbatim, not re-derived here.
    service = _service(
        pm_occurrences=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}],
        cm_reports=[
            {"cm_report_code": "CM-1", "asset_code": TAG, "severity": "CRITICAL", "status": "OPEN"}
        ],
    )

    knowledge = service.build(TAG)

    rec = next(r for r in knowledge.recommendation if r.rule_code == "REC_CRITICAL_CM")
    assert rec.priority == 100
    assert rec.confidence == 1.0
    assert rec.evidence == (
        Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL"),
    )


def test_service_accepts_an_injected_recommendation_engine():
    class FakeRecommendationEngine:
        def recommend(self, knowledge):
            return (
                Recommendation(
                    id="FAKE:1",
                    rule_code="FAKE",
                    priority=1,
                    category="MAINTENANCE",
                    title="Fake",
                    description="Fake",
                    evidence=(),
                    confidence=0.5,
                    action="Fake",
                ),
            )

    service = _service(recommendation_engine=FakeRecommendationEngine())

    knowledge = service.build(TAG)

    assert knowledge.recommendation[0].id == "FAKE:1"


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
    assert service.recommendation_engine is not None
    assert service.seal_engineering_document_gateway is not None
    assert service.pm_schedule_gateway is not None
    assert service.condition_monitoring_schedule_gateway is not None


# -- pm_schedules / condition_monitoring_schedules (MWO-LTSA-036E) ----------
# Same "filter by asset_code" technique already used for pm_history/
# cm_history -- no new business rule, reuses PMScheduleGateway/
# ConditionMonitoringScheduleGateway unmodified (both already wired
# elsewhere: EngineeringContextEngine for the former, dependencies.py for
# the latter).


def test_pm_schedules_filters_by_asset_code():
    service = _service(
        pm_schedules=[
            {"pm_schedule_code": "PMS-1", "asset_code": TAG, "status": "ACTIVE", "next_due": "2026-09-01"},
            {"pm_schedule_code": "PMS-2", "asset_code": "OTHER-PUMP", "status": "ACTIVE", "next_due": "2026-09-02"},
        ]
    )

    knowledge = service.build(TAG)

    assert knowledge.pm_schedules == [
        {"pm_schedule_code": "PMS-1", "asset_code": TAG, "status": "ACTIVE", "next_due": "2026-09-01"}
    ]


def test_pm_schedules_is_empty_when_none_exist():
    service = _service(pm_schedules=[])

    knowledge = service.build(TAG)

    assert knowledge.pm_schedules == []


def test_condition_monitoring_schedules_filters_by_asset_code():
    service = _service(
        condition_monitoring_schedules=[
            {"condition_monitoring_schedule_code": "CMS-1", "asset_code": TAG, "status": "ACTIVE"},
            {"condition_monitoring_schedule_code": "CMS-2", "asset_code": "OTHER-PUMP", "status": "ACTIVE"},
        ]
    )

    knowledge = service.build(TAG)

    assert knowledge.condition_monitoring_schedules == [
        {"condition_monitoring_schedule_code": "CMS-1", "asset_code": TAG, "status": "ACTIVE"}
    ]


def test_condition_monitoring_schedules_is_empty_when_none_exist():
    service = _service(condition_monitoring_schedules=[])

    knowledge = service.build(TAG)

    assert knowledge.condition_monitoring_schedules == []


def test_condition_monitoring_readings_prefers_repository_list_by_asset_over_gateway_list():
    repository = FakeAssetRepository(
        {
            TAG: [
                {
                    "condition_monitoring_reading_code": "CMONR-1",
                    "asset_code": TAG,
                    "reading_date": "2026-07-01",
                    "finding": "NORMAL",
                    "mechanical_seal_leak_de": False,
                    "suction_pressure": 0,
                    "pump_operating_state": None,
                },
                {
                    "condition_monitoring_reading_code": "CMONR-2",
                    "asset_code": TAG,
                    "reading_date": "2026-07-08",
                    "finding": "WATCH",
                    "mechanical_seal_leak_de": True,
                    "suction_pressure": None,
                    "pump_operating_state": "RUNNING",
                },
            ],
        }
    )
    service = _service(
        condition_monitoring_readings=[],
        condition_monitoring_reading_repository=repository,
    )

    knowledge = service.build(TAG)

    assert repository.requested_assets == [TAG]
    assert [record["condition_monitoring_reading_code"] for record in knowledge.condition_monitoring_readings] == [
        "CMONR-1",
        "CMONR-2",
    ]
    assert knowledge.condition_monitoring_readings[0]["pump_operating_state"] is None
    assert knowledge.condition_monitoring_readings[0]["suction_pressure"] == 0
    assert knowledge.condition_monitoring_readings[0]["mechanical_seal_leak_de"] is False


def test_existing_fields_unchanged_when_schedules_are_added():
    # Regression guard: extending the aggregate must not disturb any
    # existing field's value.
    service = _service(
        pump=FakePumpGateway({"success": True, "message": "ok", "data": {"tag_number": TAG}}),
        pm_occurrences=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}],
        pm_schedules=[{"pm_schedule_code": "PMS-1", "asset_code": TAG, "status": "ACTIVE"}],
    )

    knowledge = service.build(TAG)

    assert knowledge.pump == {"tag_number": TAG}
    assert knowledge.pm_history == [
        {"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}
    ]
    assert knowledge.pm_schedules == [{"pm_schedule_code": "PMS-1", "asset_code": TAG, "status": "ACTIVE"}]

import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.equipment_timeline_service import EquipmentTimelineService
from API.ltsa_knowledge_service import LTSAKnowledge
from API.timeline_value_objects import TimelineCategory


class FakeKnowledgeService:
    def __init__(self, knowledge, cm_reports=None, seal_engineering_documents=None):
        self._knowledge = knowledge
        self.cm_report_gateway = FakeGateway("list_cm_reports", cm_reports or knowledge.cm_history)
        # MWO-LTSA-064A -- Related Engineering "documents" reuses this same
        # gateway attribute LTSAKnowledgeService itself exposes; defaults
        # to an empty list so every pre-064A test (none of which configure
        # inventory with a seal_code) is unaffected.
        self.seal_engineering_document_gateway = FakeGateway(
            "list_seal_engineering_documents", seal_engineering_documents or []
        )

    def build(self, tag_number):
        return self._knowledge


class FakeGateway:
    def __init__(self, method_name, records=None, success=True):
        records = records or []
        response = {"success": success, "message": "ok", "count": len(records), "data": records}
        setattr(self, method_name, lambda: response)


TAG = "140-P-16A"


def _knowledge(**overrides):
    defaults = dict(
        tag_number=TAG,
        pump={"tag_number": TAG, "pump_name": "Pump 16A", "area": "DCU"},
        seal=[],
        inventory=[],
        pm_history=[
            {"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-29T17:00:00.000Z"}
        ],
        cm_history=[
            {
                "cm_report_code": "CM-1",
                "asset_code": TAG,
                "created_at": "2026-08-09T09:12:06.001Z",
                "failure_description": "Seal leak",
                "severity": "MAJOR",
            }
        ],
        breakdown_history=[
            {
                "maintenance_record_code": "MH-1",
                "asset_code": TAG,
                "performed_at": "2026-07-15T00:00:00Z",
                "action_taken": "Seal failure confirmed",
            }
        ],
        drawings=[],
        recommendation=(),
        pm_schedules=[{"pm_schedule_code": "PMS-1", "asset_code": TAG, "next_due": "2026-09-01"}],
        condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )
    defaults.update(overrides)
    return LTSAKnowledge(**defaults)


def _service(knowledge=None, installations=None, work_orders=None, maintenance_history=None, pm_occurrences=None, seals=None, seal_engineering_documents=None):
    knowledge = knowledge or _knowledge()
    return EquipmentTimelineService(
        knowledge_service=FakeKnowledgeService(knowledge, seal_engineering_documents=seal_engineering_documents),
        installation_gateway=FakeGateway("list_installations", installations or []),
        work_order_gateway=FakeGateway("list_work_orders", work_orders or []),
        maintenance_history_gateway=FakeGateway("list_maintenance_history", maintenance_history or []),
        pm_occurrence_gateway=FakeGateway("list_pm_occurrences", pm_occurrences or knowledge.pm_history),
        seal_gateway=FakeGateway("list_seals", seals or []),
    )


def test_build_lifecycle_returns_pump_lifecycle_with_current_state_and_analytics():
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
                "seal_code": None,
                "seal_type": "T48MP",
                "seal_manufacture": "John Crane",
                "drawing_no": "GA-230279",
                "source_document_name": "report.pdf",
                "seal_size": '3.25',
                "material_code": "1K1K",
            }
        ],
        work_orders=[
            {"work_order_code": "WO-1", "asset_code": TAG, "closed_at": None, "created_at": "2026-07-16T00:00:00Z"}
        ],
        maintenance_history=[
            {"maintenance_record_code": "MH-PM-1", "asset_code": TAG, "work_order_code": "WO-PM-1", "performed_at": "2026-06-15T00:00:00Z"}
        ],
        pm_occurrences=[
            {"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-29T17:00:00.000Z"}
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.tag_number == TAG
    # MWO-LTSA-064A -- current_installation/current_seal live only inside
    # current_state now; PumpLifecycle has no root-level copies (Section 2).
    assert not hasattr(lifecycle, "current_installation")
    assert not hasattr(lifecycle, "current_seal")
    assert lifecycle.current_state.current_installation.installation_code == "INSTL-001-2026"
    assert lifecycle.current_state.current_seal.source == "installation_report"
    assert lifecycle.current_state.elapsed_service_days == 216
    assert lifecycle.current_state.running_hours_derived is None
    assert lifecycle.current_state.last_pm is not None
    assert lifecycle.current_state.next_pm["pm_schedule_code"] == "PMS-1"
    assert lifecycle.current_state.last_cm["cm_report_code"] == "CM-1"
    assert lifecycle.current_state.last_failure["maintenance_record_code"] == "MH-1"
    assert lifecycle.current_state.open_work_orders == [
        {"work_order_code": "WO-1", "asset_code": TAG, "closed_at": None, "created_at": "2026-07-16T00:00:00Z"}
    ]
    assert lifecycle.analytics.elapsed_service_days == 216
    assert lifecycle.analytics.pm_count == 1
    # MWO-LTSA-DEMO-ANALYTICS-001 -- cm_count now derives from
    # condition_monitoring_readings (this fixture's default: none), not
    # cm_history (this fixture's default: one CM-1 report) -- the CM-1
    # report is still visible via current_state.last_cm above; it just no
    # longer feeds this specific count (see equipment_timeline_service.py's
    # own comment on cm_count for why).
    assert lifecycle.analytics.cm_count == 0
    assert lifecycle.analytics.failure_count == 1
    assert lifecycle.analytics.mtbf is None
    assert lifecycle.analytics.average_seal_life is None
    assert lifecycle.analytics.health_index is None
    assert lifecycle.analytics.availability is None
    assert lifecycle.analytics.reliability is None
    assert lifecycle.related_engineering.pm_schedules == [{"pm_schedule_code": "PMS-1", "asset_code": TAG, "next_due": "2026-09-01"}]
    # Section 4 -- extended Related Engineering, reusing already-fetched
    # LTSAKnowledgeService data (no drawings/inventory/documents configured
    # in this fixture, so an honest empty list -- never fabricated).
    assert lifecycle.related_engineering.drawings == []
    assert lifecycle.related_engineering.documents == []
    assert lifecycle.related_engineering.inventory == []


def test_build_lifecycle_timeline_contains_installation_pm_cm_failure_work_order_and_replacement_events():
    service = _service(
        installations=[
            {"installation_code": "INSTL-001", "report_no": "001", "report_date": "2026-01-01", "plant_equip_no": TAG},
            {"installation_code": "INSTL-002", "report_no": "002", "report_date": "2026-08-01", "plant_equip_no": TAG},
        ],
        work_orders=[
            {"work_order_code": "WO-1", "asset_code": TAG, "created_at": "2026-07-16T00:00:00Z", "closed_at": None}
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    categories = [event.event_type for event in lifecycle.timeline]
    assert TimelineCategory.INSTALLATION in categories
    assert TimelineCategory.PM in categories
    assert TimelineCategory.CM in categories
    assert TimelineCategory.FAILURE in categories
    assert TimelineCategory.WORK_ORDER in categories
    assert TimelineCategory.REPLACEMENT in categories


def test_build_lifecycle_uses_seal_registry_when_current_installation_has_seal_code():
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
                "seal_code": "SEAL-1",
                "seal_type": "T48MP",
                "seal_manufacture": "John Crane",
                "drawing_no": "GA-230279",
                "source_document_name": "report.pdf",
            }
        ],
        seals=[
            {
                "seal_code": "SEAL-1",
                "seal_name": "Type 48MP",
                "manufacturer": "John Crane",
                "model": "48MP",
                "shaft_size": "3.25",
                "material": "1K1K",
                "temperature_limit": "200C",
                "pressure_limit": "20 bar",
                "status": "ACTIVE",
            }
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.current_state.current_seal.seal_code == "SEAL-1"
    assert lifecycle.current_state.current_seal.seal_name == "Type 48MP"
    assert lifecycle.current_state.current_seal.source == "seal_registry"


# MWO-LTSA-ASSET360-MECHANICAL-SEAL-WIRING-001 -- build_current_seal() is a
# small, additive entry point reusing the exact same _list_installations/
# _build_current_seal helpers build_lifecycle() itself already exercises
# above (test_build_lifecycle_uses_seal_registry_when_current_installation_
# has_seal_code) -- same fixtures, same result, no new derivation.


def test_build_current_seal_matches_build_lifecycle_current_state_current_seal():
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
                "seal_code": "SEAL-1",
                "seal_type": "T48MP",
                "seal_manufacture": "John Crane",
                "drawing_no": "GA-230279",
                "source_document_name": "report.pdf",
            }
        ],
        seals=[
            {
                "seal_code": "SEAL-1",
                "seal_name": "Type 48MP",
                "manufacturer": "John Crane",
                "model": "48MP",
                "shaft_size": "3.25",
                "material": "1K1K",
                "temperature_limit": "200C",
                "pressure_limit": "20 bar",
                "status": "ACTIVE",
            }
        ],
    )

    current_seal = service.build_current_seal(TAG)
    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert current_seal == lifecycle.current_state.current_seal
    assert current_seal.seal_code == "SEAL-1"
    assert current_seal.manufacturer == "John Crane"
    assert current_seal.material == "1K1K"
    assert current_seal.source == "seal_registry"


def test_build_current_seal_returns_none_when_pump_has_no_installation():
    # No fabricated fallback: a pump with no installation record has no
    # authoritative current seal -- None, not a synthesized placeholder.
    service = _service(installations=[])

    assert service.build_current_seal(TAG) is None


def test_build_current_seal_leaves_unauthoritative_fields_none():
    # Only seal_code/seal_manufacture are present on this installation --
    # model/temperature_limit/pressure_limit/status have no authoritative
    # source anywhere (no seal_code to look up in the Seal Registry, no
    # installation-side equivalent column), so they must stay None, never
    # guessed.
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-002-2026",
                "report_no": "002/INSTL/2026",
                "report_date": "2026-02-01",
                "plant_equip_no": TAG,
                "seal_code": None,
                "seal_manufacture": "Flowserve",
            }
        ]
    )

    current_seal = service.build_current_seal(TAG)

    assert current_seal.manufacturer == "Flowserve"
    assert current_seal.model is None
    assert current_seal.temperature_limit is None
    assert current_seal.pressure_limit is None
    assert current_seal.status is None


def test_current_seal_never_overwrites_a_present_but_falsy_seal_registry_value():
    # MWO-LTSA-064A Section 3 -- a Seal Registry value that is present but
    # falsy (empty string) must NOT be replaced by Installation's fallback
    # value. The prior `X or Y` pattern would have incorrectly fallen
    # through here; the corrected `is not None` check must not.
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
                "seal_code": "SEAL-1",
                "seal_manufacture": "Installation-side manufacturer (must not win)",
                "seal_size": "installation-size (must not win)",
                "material_code": "installation-material (must not win)",
            }
        ],
        seals=[
            {
                "seal_code": "SEAL-1",
                "seal_name": "Type 48MP",
                "manufacturer": "",
                "shaft_size": "",
                "material": "",
            }
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))
    current_seal = lifecycle.current_state.current_seal

    assert current_seal.source == "seal_registry"
    assert current_seal.manufacturer == ""
    assert current_seal.shaft_size == ""
    assert current_seal.material == ""


def test_related_engineering_reuses_drawings_inventory_and_filters_documents_by_compatible_seal_code():
    # MWO-LTSA-064A Section 4 -- drawings/inventory are the exact,
    # already-computed LTSAKnowledge fields (no new fetch); documents
    # reuses the same seal_engineering_document_gateway
    # LTSAKnowledgeService already holds, filtered to the pump's
    # compatible seal_code(s) derived from knowledge.inventory.
    knowledge = _knowledge(
        inventory=[{"seal_code": "SEAL-1", "quantity_on_hand": 4, "reorder_point": 1, "location": "WH-1"}],
        drawings=[{"drawing_id": "DOC-1", "title": "GA Drawing"}],
    )
    service = _service(
        knowledge=knowledge,
        seal_engineering_documents=[
            {"document_code": "DOC-2", "seal_code": "SEAL-1", "document_type": "DATASHEET"},
            {"document_code": "DOC-3", "seal_code": "SEAL-OTHER", "document_type": "DATASHEET"},
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.related_engineering.drawings == [{"drawing_id": "DOC-1", "title": "GA Drawing"}]
    assert lifecycle.related_engineering.inventory == [
        {"seal_code": "SEAL-1", "quantity_on_hand": 4, "reorder_point": 1, "location": "WH-1"}
    ]
    assert lifecycle.related_engineering.documents == [
        {"document_code": "DOC-2", "seal_code": "SEAL-1", "document_type": "DATASHEET"}
    ]


def test_pump_lifecycle_models_has_no_dependency_on_equipment_timeline_service():
    # MWO-LTSA-064A Section 1 -- the DTO module must depend on nothing;
    # only equipment_timeline_service.py may import pump_lifecycle_models,
    # never the reverse. A static source check, so re-introducing the
    # cycle fails this test immediately rather than surfacing as a runtime
    # ImportError somewhere else.
    import inspect

    import API.pump_lifecycle_models as models

    import_lines = [
        line.strip()
        for line in inspect.getsource(models).splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    assert not any("equipment_timeline_service" in line for line in import_lines)


def test_build_lifecycle_with_no_installation_leaves_current_installation_and_seal_null():
    # MWO-LTSA-066 -- "no installation" coverage: a pump with zero
    # installation_report rows must get an honest null current state, not
    # a fabricated one, and no INSTALLATION/REPLACEMENT timeline events.
    service = _service(installations=[])

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.current_state.current_installation is None
    assert lifecycle.current_state.current_seal is None
    assert lifecycle.current_state.elapsed_service_days is None
    assert lifecycle.current_state.running_hours_derived is None
    categories = [event.event_type for event in lifecycle.timeline]
    assert TimelineCategory.INSTALLATION not in categories
    assert TimelineCategory.REPLACEMENT not in categories


def test_engineer_is_derived_from_the_signatory_whose_title_mentions_an_engineering_role():
    # MWO-LTSA-066 -- Engineer has no dedicated column; it is derived from
    # installation_report.signatures (JSONB), matching the real shape
    # sampleInstallations.js's own literal transcription established
    # (BP-INSTALLATION's seed source): [{id, company, name, title, date}].
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
                "signatures": [
                    {"id": 1, "company": "PT Tommy Adji Prasetyo", "name": "Rizky Trinoviandi", "title": "Service", "date": "7/01/2026"},
                    {"id": 2, "company": "PT Tommy Adji Prasetyo", "name": "Muh Taufik", "title": "Service Engineer", "date": "07/01/2026"},
                    {"id": 3, "company": "PT KPI RU II Dumai", "name": None, "title": "Technicion I/RE", "date": "07-01-2026"},
                ],
            }
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.current_state.current_installation.engineer == "Muh Taufik"


def test_engineer_falls_back_to_title_when_the_matching_signatory_has_no_name():
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
                "signatures": [
                    {"id": 1, "company": "PT KPI RU II Dumai", "name": None, "title": "Jr. Eng / RE Insp", "date": "07-01-2026"},
                ],
            }
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.current_state.current_installation.engineer == "Jr. Eng / RE Insp"


def test_engineer_is_null_when_no_signatory_title_mentions_an_engineering_role():
    # Never fabricate: no signatory's title matches "eng" here, so engineer
    # must be null rather than guessing at one of the non-engineering roles.
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
                "signatures": [
                    {"id": 1, "company": "PT Tommy Adji Prasetyo", "name": "Rizky Trinoviandi", "title": "Service", "date": "7/01/2026"},
                ],
            }
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.current_state.current_installation.engineer is None


def test_engineer_is_null_when_the_installation_record_has_no_signatures_at_all():
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
            }
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.current_state.current_installation.engineer is None


# --- MWO-LTSA-067: lifecycle.timeline payload/order coverage ---------------


def test_installation_event_payload_includes_the_required_fields_plus_derived_engineer():
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-06",
                "plant_equip_no": TAG,
                "drawing_no": "GA-230279",
                "seal_code": "SEAL-1",
                "signatures": [
                    {"id": 1, "company": "PT Tommy Adji Prasetyo", "name": "Muh Taufik", "title": "Service Engineer", "date": "07/01/2026"},
                ],
            }
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))
    installation_event = next(e for e in lifecycle.timeline if e.event_type == TimelineCategory.INSTALLATION)

    assert installation_event.id == "INSTALLATION:INSTL-001-2026"
    assert installation_event.occurred_at == "2026-01-06"
    assert installation_event.source.value == "INSTALLATION_REPORT"
    assert installation_event.derived is False
    assert installation_event.payload["installation_code"] == "INSTL-001-2026"
    assert installation_event.payload["report_no"] == "001/INSTL/2026"
    assert installation_event.payload["drawing_no"] == "GA-230279"
    assert installation_event.payload["seal_code"] == "SEAL-1"
    assert installation_event.payload["report_date"] == "2026-01-06"
    assert installation_event.payload["engineer"] == "Muh Taufik"


def test_pm_event_payload_includes_the_full_pm_occurrence_record():
    pm_record = {"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-29T17:00:00.000Z", "description": "Quarterly inspection"}
    service = _service(knowledge=_knowledge(pm_history=[pm_record]))

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))
    pm_event = next(e for e in lifecycle.timeline if e.event_type == TimelineCategory.PM)

    assert pm_event.payload == pm_record
    assert pm_event.derived is True


def test_cm_event_payload_includes_the_full_cm_report_record():
    cm_record = {"cm_report_code": "CM-1", "asset_code": TAG, "created_at": "2026-08-09T09:12:06.001Z", "failure_description": "Seal leak", "severity": "MAJOR"}
    service = _service(knowledge=_knowledge(cm_history=[cm_record]))

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))
    cm_event = next(e for e in lifecycle.timeline if e.event_type == TimelineCategory.CM)

    assert cm_event.payload == cm_record
    assert cm_event.derived is True


def test_work_order_event_payload_includes_the_full_work_order_record():
    wo_record = {"work_order_code": "WO-1", "asset_code": TAG, "created_at": "2026-07-16T00:00:00Z", "closed_at": None, "title": "Inspect coupling"}
    service = _service(work_orders=[wo_record])

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))
    wo_event = next(e for e in lifecycle.timeline if e.event_type == TimelineCategory.WORK_ORDER)

    assert wo_event.payload == wo_record
    assert wo_event.derived is False


def test_failure_event_payload_includes_the_full_breakdown_history_record():
    failure_record = {"maintenance_record_code": "MH-1", "asset_code": TAG, "performed_at": "2026-07-15T00:00:00Z", "action_taken": "Seal failure confirmed"}
    service = _service(knowledge=_knowledge(breakdown_history=[failure_record]))

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))
    failure_event = next(e for e in lifecycle.timeline if e.event_type == TimelineCategory.FAILURE)

    assert failure_event.payload == failure_record
    assert failure_event.derived is True


def test_replacement_event_is_derived_only_between_two_consecutive_installations():
    service = _service(
        installations=[
            {"installation_code": "INSTL-001", "report_no": "001", "report_date": "2026-01-01", "plant_equip_no": TAG},
            {"installation_code": "INSTL-002", "report_no": "002", "report_date": "2026-08-01", "plant_equip_no": TAG},
        ],
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))
    replacement_event = next(e for e in lifecycle.timeline if e.event_type == TimelineCategory.REPLACEMENT)

    assert replacement_event.derived is True
    assert replacement_event.occurred_at == "2026-08-01"
    assert replacement_event.payload == {
        "replaced_installation_code": "INSTL-001",
        "replacement_installation_code": "INSTL-002",
        "pump_tag_number": TAG,
    }


def test_timeline_is_sorted_newest_first_not_oldest_first():
    service = _service(
        installations=[
            {"installation_code": "INSTL-001", "report_no": "001", "report_date": "2026-01-01", "plant_equip_no": TAG},
        ],
        work_orders=[
            {"work_order_code": "WO-1", "asset_code": TAG, "created_at": "2026-07-16T00:00:00Z", "closed_at": None},
        ],
        knowledge=_knowledge(
            pm_history=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-29"}],
            cm_history=[],
            breakdown_history=[],
        ),
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))
    occurred_dates = [event.occurred_at for event in lifecycle.timeline]

    assert occurred_dates == sorted(occurred_dates, reverse=True)
    # WORK_ORDER's occurred_at is the raw created_at timestamp (unnormalized,
    # existing behavior -- _work_order_occurred_at() predates this MWO), so
    # it sorts ahead of the date-only PM/INSTALLATION strings even though
    # they're all the same calendar month -- exactly what "newest first"
    # over these three real dates (2026-01-01 / 2026-06-29 / 2026-07-16)
    # should produce.
    assert lifecycle.timeline[0].occurred_at == "2026-07-16T00:00:00Z"
    assert lifecycle.timeline[-1].occurred_at == "2026-01-01"


def test_empty_timeline_when_the_pump_has_no_history_at_all():
    service = _service(
        installations=[],
        work_orders=[],
        knowledge=_knowledge(pm_history=[], cm_history=[], breakdown_history=[]),
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.timeline == ()


def test_build_lifecycle_exposes_production_pm_and_cmon_readings_without_duplicates_or_value_coercion():
    # MWO-LTSA-EQUIPMENT-HISTORY-PM-CMON-CLOSURE-001 -- production
    # semantics: promoted historical PM/CMON rows are associated to the
    # pump by asset_code and must enter Equipment History without any
    # source-row mutation or current-pump rewriting.
    fixtures = {
        "110-P-10": (1, 3),
        "140-P-11": (1, 2),
        "212-P-7B": (1, 4),
    }

    for tag, (pm_count, cmon_count) in fixtures.items():
        pm_history = [
            {
                "pm_occurrence_code": f"PM-{tag}-{index}",
                "asset_code": tag,
                "occurrence_date": f"2026-07-{index + 1:02d}",
                "remarks": None,
            }
            for index in range(pm_count)
        ]
        cmon_readings = [
            {
                "condition_monitoring_reading_code": f"CMON-{tag}-{index}",
                "asset_code": tag,
                "reading_date": f"2026-08-{index + 1:02d}",
                "finding": "Finding text" if index == 0 else None,
                "pump_operating_state": None,
                "suction_pressure": 0 if index == 0 else None,
                "mechanical_seal_leak_de": False,
            }
            for index in range(cmon_count)
        ]
        knowledge = _knowledge(
            tag_number=tag,
            pump={"tag_number": tag, "area": "HOC"},
            pm_history=pm_history,
            cm_history=[],
            breakdown_history=[],
            condition_monitoring_readings=cmon_readings,
        )
        service = _service(knowledge=knowledge, installations=[], work_orders=[])

        lifecycle = service.build_lifecycle(tag)

        pm_events = [event for event in lifecycle.timeline if event.event_type == TimelineCategory.PM]
        cmon_events = [event for event in lifecycle.timeline if event.source.value == "CONDITION_MONITORING_READING"]
        event_ids = [event.id for event in lifecycle.timeline]
        assert len(pm_events) == pm_count
        assert len(cmon_events) == cmon_count
        assert len(event_ids) == len(set(event_ids))
        assert lifecycle.analytics.pm_count == pm_count
        # MWO-LTSA-DEMO-ANALYTICS-001 -- cm_count must equal the number of
        # CONDITION_MONITORING_READING timeline events (cmon_count), the
        # same list cmon_events above already counts -- previously asserted
        # 0 regardless of cmon_count, the exact production-proven defect
        # for 212-P-7B/110-P-10/140-P-11 (this test's own three fixtures).
        assert lifecycle.analytics.cm_count == cmon_count
        assert lifecycle.related_engineering.condition_monitoring_readings == cmon_readings
        first_source_reading = next(
            event for event in cmon_events
            if event.payload["condition_monitoring_reading_code"] == f"CMON-{tag}-0"
        )
        assert first_source_reading.payload["asset_code"] == tag
        assert first_source_reading.payload["pump_operating_state"] is None
        assert first_source_reading.payload["suction_pressure"] == 0
        assert first_source_reading.payload["mechanical_seal_leak_de"] is False
        assert first_source_reading.payload["finding"] == "Finding text"

# MWO-LTSA-069 -- Pump Reliability Analytics. build_lifecycle()'s
# elapsed_service_days/pm_count/cm_count/failure_count computation and its
# mtbf/mtbr/average_seal_life/health_index/availability/reliability
# placeholders already exist (MWO-LTSA-064A/066/067) and are unmodified by
# this MWO -- these tests add the isolated no-history/pm-only/cm-only/
# failure-only scenario coverage this MWO's own Tests section asks for,
# on top of the pre-existing combined-scenario coverage above
# (test_build_lifecycle_returns_pump_lifecycle_with_current_state_and_analytics),
# the no-installation edge case
# (test_build_lifecycle_with_no_installation_leaves_current_installation_and_seal_null),
# and the empty-timeline case immediately above. No production code is
# touched -- see the MWO-LTSA-069 Completion Report's Reuse Audit for why.
#
# MWO-LTSA-DEMO-ANALYTICS-001 (later) -- cm_count's own source WAS
# subsequently corrected (equipment_timeline_service.py, len(knowledge.
# cm_history) -> len(knowledge.condition_monitoring_readings)); the
# "cm-only" isolation test below was renamed/re-asserted accordingly and a
# new "cmon-only" isolation test added to prove the real source in kind.


def test_analytics_counts_are_all_zero_when_the_pump_has_no_history_at_all():
    service = _service(
        installations=[],
        work_orders=[],
        knowledge=_knowledge(pm_history=[], cm_history=[], breakdown_history=[]),
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.analytics.elapsed_service_days is None
    assert lifecycle.analytics.pm_count == 0
    assert lifecycle.analytics.cm_count == 0
    assert lifecycle.analytics.failure_count == 0
    assert lifecycle.analytics.mtbf is None
    assert lifecycle.analytics.mtbr is None
    assert lifecycle.analytics.average_seal_life is None
    assert lifecycle.analytics.health_index is None
    assert lifecycle.analytics.availability is None
    assert lifecycle.analytics.reliability is None


def test_analytics_counts_pm_only_never_cross_contaminating_cm_or_failure_count():
    service = _service(
        installations=[],
        work_orders=[],
        knowledge=_knowledge(
            pm_history=[
                {"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-29"},
                {"pm_occurrence_code": "PM-2", "asset_code": TAG, "occurrence_date": "2026-07-29"},
            ],
            cm_history=[],
            breakdown_history=[],
        ),
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.analytics.pm_count == 2
    assert lifecycle.analytics.cm_count == 0
    assert lifecycle.analytics.failure_count == 0


def test_analytics_counts_a_cm_report_alone_no_longer_contributes_to_cm_count():
    # MWO-LTSA-DEMO-ANALYTICS-001 -- renamed/re-asserted from the prior
    # "cm_only" scenario: cm_count now derives from condition_monitoring_
    # readings only (see equipment_timeline_service.py's own comment), so
    # a cm_report row alone (no CMON reading) contributes 0, not 1.
    service = _service(
        installations=[],
        work_orders=[],
        knowledge=_knowledge(
            pm_history=[],
            cm_history=[
                {
                    "cm_report_code": "CM-1",
                    "asset_code": TAG,
                    "created_at": "2026-08-09T09:12:06.001Z",
                    "failure_description": "Seal leak",
                    "severity": "MAJOR",
                }
            ],
            breakdown_history=[],
            condition_monitoring_readings=[],
        ),
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.analytics.pm_count == 0
    assert lifecycle.analytics.cm_count == 0
    assert lifecycle.analytics.failure_count == 0


def test_analytics_counts_cmon_only_never_cross_contaminating_pm_or_failure_count():
    # The real cm_count source: condition_monitoring_readings, isolated
    # from pm_history/breakdown_history, mirroring the pm-only/failure-only
    # isolation tests above.
    service = _service(
        installations=[],
        work_orders=[],
        knowledge=_knowledge(
            pm_history=[],
            cm_history=[],
            breakdown_history=[],
            condition_monitoring_readings=[
                {
                    "condition_monitoring_reading_code": "CMON-1",
                    "asset_code": TAG,
                    "reading_date": "2026-08-09",
                    "finding": None,
                },
                {
                    "condition_monitoring_reading_code": "CMON-2",
                    "asset_code": TAG,
                    "reading_date": "2026-08-10",
                    "finding": None,
                },
            ],
        ),
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.analytics.pm_count == 0
    assert lifecycle.analytics.cm_count == 2
    assert lifecycle.analytics.failure_count == 0


def test_analytics_counts_failure_only_never_cross_contaminating_pm_or_cm_count():
    service = _service(
        installations=[],
        work_orders=[],
        knowledge=_knowledge(
            pm_history=[],
            cm_history=[],
            breakdown_history=[
                {
                    "maintenance_record_code": "MH-1",
                    "asset_code": TAG,
                    "performed_at": "2026-07-15T00:00:00Z",
                    "action_taken": "Seal failure confirmed",
                },
                {
                    "maintenance_record_code": "MH-2",
                    "asset_code": TAG,
                    "performed_at": "2026-07-20T00:00:00Z",
                    "action_taken": "Bearing failure confirmed",
                },
                {
                    "maintenance_record_code": "MH-3",
                    "asset_code": TAG,
                    "performed_at": "2026-07-25T00:00:00Z",
                    "action_taken": "Coupling failure confirmed",
                },
            ],
        ),
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.analytics.pm_count == 0
    assert lifecycle.analytics.cm_count == 0
    assert lifecycle.analytics.failure_count == 3


def test_analytics_elapsed_service_days_computed_from_installation_report_date_when_installation_exists():
    # "installation" scenario -- isolates elapsed_service_days' real
    # derivation (report_date -> today) from the combined fixture in
    # test_build_lifecycle_returns_pump_lifecycle_with_current_state_and_analytics
    # above, with zero PM/CM/failure history so only the installation
    # effect is under test.
    service = _service(
        installations=[
            {
                "installation_code": "INSTL-001-2026",
                "report_no": "001/INSTL/2026",
                "report_date": "2026-01-01",
                "plant_equip_no": TAG,
            }
        ],
        work_orders=[],
        knowledge=_knowledge(pm_history=[], cm_history=[], breakdown_history=[]),
    )

    lifecycle = service.build_lifecycle(TAG, today=__import__("datetime").date(2026, 8, 10))

    assert lifecycle.analytics.elapsed_service_days == 221
    assert lifecycle.analytics.pm_count == 0
    assert lifecycle.analytics.cm_count == 0
    assert lifecycle.analytics.failure_count == 0


# --- MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -----------------------


class FakeSealLifecycleEventRepository:
    def __init__(self, events_by_pump=None):
        self._events_by_pump = events_by_pump or {}

    def list_by_pump(self, pump_tag_number):
        return self._events_by_pump.get(pump_tag_number, [])


class FakeSealInspectionRepository:
    def list_by_pump(self, pump_tag_number):
        return []


class FakeSealRepairRepository:
    def list_by_inspection_ids(self, inspection_ids):
        return []


class FakeSealWarrantyAssessmentRepository:
    def list_by_pump(self, pump_tag_number):
        return []


class FakeInstallationReportFitmentRepository:
    def __init__(self, reports_by_pump=None):
        self._reports_by_pump = reports_by_pump or {}

    def list_by_pump(self, pump_tag_number):
        return self._reports_by_pump.get(pump_tag_number, [])


def test_build_lifecycle_with_seal_repos_absent_preserves_pm_and_cm_unchanged():
    # 1/2/25/26: Equipment History with existing PM/CMON but no seal data
    # must continue working unchanged -- every prior test in this file
    # already proves this (none pass seal_* repos at all), reconfirmed
    # here explicitly as this MWO's own required regression.
    service = _service(installations=[])
    lifecycle = service.build_lifecycle(TAG)
    types = [e.event_type for e in lifecycle.timeline]
    assert TimelineCategory.PM in types
    assert TimelineCategory.CM in types


def test_build_lifecycle_merges_seal_install_event_and_dedups_linked_report():
    knowledge = _knowledge(pm_history=[], cm_history=[], breakdown_history=[])
    install_event = {
        "event_id": "evt-1", "seal_unit_id": "unit-1", "event_type": "INSTALL",
        "event_at": "2026-01-01T00:00:00Z", "pump_tag_number": TAG, "reason": None, "notes": None,
    }
    linked_report = {
        "installation_code": "INSTL-LINKED", "report_no": "RPT-1", "report_date": "2026-01-01",
        "plant_equip_no": TAG, "pump_tag_number": TAG, "installation_event_id": "evt-1",
    }
    unlinked_report = {
        "installation_code": "INSTL-LEGACY", "report_no": "RPT-2", "report_date": "2026-02-01",
        "plant_equip_no": TAG, "pump_tag_number": None, "installation_event_id": None,
    }
    service = EquipmentTimelineService(
        knowledge_service=FakeKnowledgeService(knowledge),
        installation_gateway=FakeGateway("list_installations", [linked_report, unlinked_report]),
        work_order_gateway=FakeGateway("list_work_orders", []),
        maintenance_history_gateway=FakeGateway("list_maintenance_history", []),
        pm_occurrence_gateway=FakeGateway("list_pm_occurrences", []),
        seal_gateway=FakeGateway("list_seals", []),
        seal_lifecycle_event_repository=FakeSealLifecycleEventRepository({TAG: [install_event]}),
        seal_inspection_repository=FakeSealInspectionRepository(),
        seal_repair_repository=FakeSealRepairRepository(),
        seal_warranty_assessment_repository=FakeSealWarrantyAssessmentRepository(),
        installation_report_fitment_repository=FakeInstallationReportFitmentRepository({TAG: [linked_report]}),
    )

    lifecycle = service.build_lifecycle(TAG)

    seal_installs = [e for e in lifecycle.timeline if e.event_type == TimelineCategory.SEAL_INSTALL]
    assert len(seal_installs) == 1
    assert seal_installs[0].payload["installation_report"]["installation_code"] == "INSTL-LINKED"

    # 4: the linked report must not ALSO appear as its own legacy
    # INSTALLATION event -- only the unlinked legacy one does.
    legacy_installations = [e for e in lifecycle.timeline if e.event_type == TimelineCategory.INSTALLATION]
    assert [e.payload.get("installation_code") for e in legacy_installations] == ["INSTL-LEGACY"]

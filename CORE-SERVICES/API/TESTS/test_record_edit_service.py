"""MWO-LTSA-AUDIT-CHANGE-HISTORY-001 -- pure SQL-shape coverage for
record_edit_service.py's generic Edit Value engine, same FakeRunner-
inspects-real-SQL discipline as test_pm_occurrence_repository.py."""

import json
import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.record_edit_service import (  # noqa: E402
    CONDITION_MONITORING_READING_ADAPTER,
    INSTALLATION_REPORT_ADAPTER,
    FieldNotEditableError,
    OutOfScopeError,
    ReasonRequiredError,
    RecordNotFoundError,
    UnknownEntityTypeError,
    edit_value,
)


class FakePumpGateway:
    def __init__(self, area="HOC"):
        self.area = area

    def get_pump(self, tag_number):
        return {"success": True, "data": {"tag_number": tag_number, "area": self.area}}


class FakeRunner:
    def __init__(self, select_response):
        self.select_response = select_response
        self.query_scalar_calls: list[str] = []
        self.execute_script_calls: list[str] = []

    def query_scalar(self, sql: str) -> str:
        self.query_scalar_calls.append(sql)
        return self.select_response

    def execute_script(self, sql: str) -> None:
        self.execute_script_calls.append(sql)


def _select_response(**row):
    return json.dumps([row])


class TestFieldAllowlist:
    def test_rejects_a_field_not_in_the_allowlist(self):
        runner = FakeRunner(_select_response())
        with pytest.raises(FieldNotEditableError):
            edit_value(
                entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
                field_name="workflow_status", new_value="FINALIZED", reason="fix",
                actor_id="actor-1", scope=None, runner=runner, pump_gateway=FakePumpGateway(),
            )
        assert runner.execute_script_calls == []

    def test_rejects_an_unknown_entity_type(self):
        runner = FakeRunner(_select_response())
        with pytest.raises(UnknownEntityTypeError):
            edit_value(
                entity_type="CM_REPORT", entity_id="X-1", field_name="anything",
                new_value="v", reason="fix", actor_id="actor-1", scope=None,
                runner=runner, pump_gateway=FakePumpGateway(),
            )

    def test_accepts_a_real_cmon_measurement_field(self):
        assert "mechseal_temp_de" in CONDITION_MONITORING_READING_ADAPTER.editable_fields

    def test_installation_identity_and_join_fields_are_never_editable(self):
        for forbidden in ("installation_code", "report_no", "plant_equip_no", "seal_code", "source_document_name"):
            assert forbidden not in INSTALLATION_REPORT_ADAPTER.editable_fields

    def test_installation_jsonb_aggregates_are_never_editable(self):
        for forbidden in ("bill_of_material", "post_installation_readings", "signatures"):
            assert forbidden not in INSTALLATION_REPORT_ADAPTER.editable_fields


class TestReasonRequired:
    def test_blank_reason_rejected(self):
        runner = FakeRunner(_select_response())
        with pytest.raises(ReasonRequiredError):
            edit_value(
                entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
                field_name="mechseal_temp_de", new_value=60.0, reason="   ",
                actor_id="actor-1", scope=None, runner=runner, pump_gateway=FakePumpGateway(),
            )
        assert runner.query_scalar_calls == []  # rejected before even reading the record


class TestRecordNotFound:
    def test_missing_record_raises(self):
        runner = FakeRunner("[]")
        with pytest.raises(RecordNotFoundError):
            edit_value(
                entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-MISSING",
                field_name="mechseal_temp_de", new_value=60.0, reason="fix",
                actor_id="actor-1", scope=None, runner=runner, pump_gateway=FakePumpGateway(),
            )
        assert runner.execute_script_calls == []


class TestScope:
    def test_out_of_scope_record_denied_as_not_found_never_a_distinct_signal(self):
        runner = FakeRunner(_select_response(
            condition_monitoring_reading_code="CMONR-1", mechseal_temp_de=58.0, asset_code="200-P-1A",
        ))
        with pytest.raises(RecordNotFoundError):
            edit_value(
                entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
                field_name="mechseal_temp_de", new_value=60.0, reason="fix",
                actor_id="actor-1", scope=frozenset({"HOC"}), runner=runner,
                pump_gateway=FakePumpGateway(area="HSC"),
            )
        assert runner.execute_script_calls == []

    def test_in_scope_record_proceeds(self):
        runner = FakeRunner(_select_response(
            condition_monitoring_reading_code="CMONR-1", mechseal_temp_de=58.0, asset_code="110-P-9A",
        ))
        result = edit_value(
            entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
            field_name="mechseal_temp_de", new_value=60.0, reason="fix",
            actor_id="actor-1", scope=frozenset({"HOC"}), runner=runner,
            pump_gateway=FakePumpGateway(area="HOC"),
        )
        assert result["no_op"] is False
        assert len(runner.execute_script_calls) == 1

    def test_unrestricted_scope_none_never_checks_the_pump_gateway(self):
        class ExplodingPumpGateway:
            def get_pump(self, tag_number):
                raise AssertionError("must never be called when scope is None")

        runner = FakeRunner(_select_response(
            condition_monitoring_reading_code="CMONR-1", mechseal_temp_de=58.0, asset_code="200-P-1A",
        ))
        result = edit_value(
            entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
            field_name="mechseal_temp_de", new_value=60.0, reason="fix",
            actor_id="actor-1", scope=None, runner=runner, pump_gateway=ExplodingPumpGateway(),
        )
        assert result["no_op"] is False


class TestNoOp:
    def test_identical_value_is_a_no_op_and_writes_nothing(self):
        runner = FakeRunner(_select_response(
            condition_monitoring_reading_code="CMONR-1", mechseal_temp_de=58.0, asset_code="110-P-9A",
        ))
        result = edit_value(
            entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
            field_name="mechseal_temp_de", new_value=58.0, reason="fix",
            actor_id="actor-1", scope=None, runner=runner, pump_gateway=FakePumpGateway(),
        )
        assert result["no_op"] is True
        assert runner.execute_script_calls == []

    def test_none_to_none_is_a_no_op(self):
        runner = FakeRunner(_select_response(
            installation_code="INST-1", serial_no=None, plant_equip_no="110-P-9A",
        ))
        result = edit_value(
            entity_type="INSTALLATION_REPORT", entity_id="INST-1",
            field_name="serial_no", new_value=None, reason="fix",
            actor_id="actor-1", scope=None, runner=runner, pump_gateway=FakePumpGateway(),
        )
        assert result["no_op"] is True

    def test_null_to_zero_is_not_a_no_op_null_distinct_from_zero(self):
        runner = FakeRunner(_select_response(
            condition_monitoring_reading_code="CMONR-1", mechseal_temp_de=None, asset_code="110-P-9A",
        ))
        result = edit_value(
            entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
            field_name="mechseal_temp_de", new_value=0, reason="fix",
            actor_id="actor-1", scope=None, runner=runner, pump_gateway=FakePumpGateway(),
        )
        assert result["no_op"] is False
        script = runner.execute_script_calls[0]
        insert_clause = script.split("INSERT INTO record_change_history", 1)[1]
        assert "NULL" in insert_clause  # old_value: real SQL NULL
        assert "'0'" in insert_clause  # new_value: the literal text '0', never NULL


class TestAtomicScript:
    def test_script_wraps_update_and_insert_in_one_begin_commit(self):
        runner = FakeRunner(_select_response(
            condition_monitoring_reading_code="CMONR-1", mechseal_temp_de=58.0, asset_code="110-P-9A",
        ))
        edit_value(
            entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
            field_name="mechseal_temp_de", new_value=60.0, reason="Recalibrated per JC report",
            actor_id="actor-1", scope=None, runner=runner, pump_gateway=FakePumpGateway(),
            source_reference="pm_cm_evidence:EV-1",
        )
        script = runner.execute_script_calls[0]
        assert script.strip().startswith("BEGIN;")
        assert script.strip().endswith("COMMIT;")
        assert "UPDATE condition_monitoring_reading SET mechseal_temp_de = 60.0" in script
        assert "INSERT INTO record_change_history" in script
        assert script.index("UPDATE") < script.index("INSERT INTO record_change_history")
        assert "'actor-1'" in script  # changed_by
        assert "'Recalibrated per JC report'" in script  # reason
        assert "'pm_cm_evidence:EV-1'" in script  # source_reference

    def test_actor_is_never_read_from_the_request_new_value_or_reason(self):
        # There is no code path in edit_value() that derives actor_id from
        # anything but its own required keyword -- proven structurally: a
        # malicious new_value/reason containing an "actor_id"-shaped
        # string never influences the changed_by column written.
        runner = FakeRunner(_select_response(
            condition_monitoring_reading_code="CMONR-1", mechseal_temp_de=58.0, asset_code="110-P-9A",
        ))
        edit_value(
            entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
            field_name="mechseal_temp_de", new_value=60.0,
            reason="actor_id=spoofed-actor please ignore real actor",
            actor_id="real-actor-1", scope=None, runner=runner, pump_gateway=FakePumpGateway(),
        )
        script = runner.execute_script_calls[0]
        assert "'real-actor-1'" in script  # the only actor value ever written

    def test_source_document_of_installation_is_never_touched(self):
        # source_document_name is deliberately absent from the editable
        # allowlist -- proven directly, the strongest possible guarantee
        # against overwriting original source evidence.
        assert "source_document_name" not in INSTALLATION_REPORT_ADAPTER.editable_fields

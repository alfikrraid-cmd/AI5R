"""MWO-LTSA-PM-CM-INTAKE-001 -- Condition Monitoring Reading write-route
tests. Same authorization mechanism as PM Occurrence
(test_pm_occurrence_write_router.py) -- condensed to the CMON-specific
create/measurement/technical-review paths, not a full re-run of every
already-proven authorization case."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_condition_monitoring_reading_repository, get_current_user  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakeConditionMonitoringReadingRepository:
    def __init__(self, *, existing_codes=("CMONR-1",), known_assets=("G-201-01A",), bulk_failure=None):
        self.existing_codes = set(existing_codes)
        self.known_assets = set(known_assets)
        self.bulk_failure = bulk_failure
        self.calls: list[tuple] = []

    def create_draft(self, **kwargs):
        self.calls.append(("create_draft", kwargs))
        return {"condition_monitoring_reading_code": "CMONR-NEW", "workflow_status": "DRAFT", **kwargs}

    def create_ad_hoc_draft(self, **kwargs):
        self.calls.append(("create_ad_hoc_draft", kwargs))
        if kwargs["asset_code"] not in self.known_assets:
            return None
        return {
            "condition_monitoring_reading_code": "CMONR-ADHOC-NEW",
            "condition_monitoring_schedule_code": f"UNSCHEDULED::{kwargs['provenance']}",
            "workflow_status": "DRAFT",
            **kwargs,
        }

    def create_ad_hoc_batch(self, rows, **kwargs):
        self.calls.append(("create_ad_hoc_batch", rows, kwargs))
        if self.bulk_failure is not None:
            raise self.bulk_failure
        bad_assets = [row["asset_code"] for row in rows if row["asset_code"] not in self.known_assets]
        if bad_assets:
            raise ValueError(f"ad-hoc bulk create precheck failed: {len(bad_assets)} pump tag(s) unknown/ambiguous")
        # Real create_ad_hoc_batch() generates every code inside the one
        # atomic SQL script and returns exactly len(rows) rows or raises
        # -- this Fake mirrors that all-or-nothing contract, never a
        # partial list.
        return [
            {
                "condition_monitoring_reading_code": f"CMONR-BULK-{i}",
                "condition_monitoring_schedule_code": "UNSCHEDULED::MANUAL",
                "workflow_status": "DRAFT",
                **row,
                **kwargs,
            }
            for i, row in enumerate(rows)
        ]

    def update_draft(self, code, **kwargs):
        self.calls.append(("update_draft", code, kwargs))
        return None if code not in self.existing_codes else {"condition_monitoring_reading_code": code, **kwargs}

    def submit(self, code, **kwargs):
        self.calls.append(("submit", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"condition_monitoring_reading_code": code, "workflow_status": "SUBMITTED", **kwargs}

    def admin_return_for_correction(self, code, **kwargs):
        self.calls.append(("admin_return_for_correction", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"condition_monitoring_reading_code": code, "workflow_status": "RETURNED_FOR_CORRECTION", **kwargs}

    def technical_return_for_correction(self, code, **kwargs):
        self.calls.append(("technical_return_for_correction", code, kwargs))
        return None

    def technical_finalize(self, code, **kwargs):
        self.calls.append(("technical_finalize", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"condition_monitoring_reading_code": code, "workflow_status": "FINALIZED", **kwargs}

    def soft_delete(self, code, **kwargs):
        self.calls.append(("soft_delete", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"condition_monitoring_reading_code": code, "deleted_by": kwargs["deleted_by"]}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role: str, user_id: str = "actor-1", repository=None):
    fake = repository or FakeConditionMonitoringReadingRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, user_id)
    app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: fake
    return fake


def test_tap_engineer_can_create_a_reading_with_real_measurements():
    fake = _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={
            "condition_monitoring_schedule_code": "CMS-1",
            "asset_code": "G-201-01A",
            "measurements": {"suction_temp": 34.0, "mechanical_seal_leak_de": False},
        },
    )
    assert response.status_code == 200
    assert fake.calls[0][1]["measurements"]["suction_temp"] == 34.0
    assert fake.calls[0][1]["measurements"]["mechanical_seal_leak_de"] is False


def test_missing_measurement_is_null_not_zero_through_the_full_request_cycle():
    fake = _override("TAP_ENGINEER")
    client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={
            "condition_monitoring_schedule_code": "CMS-1",
            "asset_code": "G-201-01A",
            "measurements": {"suction_temp": 34.0},
        },
    )
    assert fake.calls[0][1]["measurements"]["discharge_temp"] is None
    assert fake.calls[0][1]["measurements"]["vertical_vibration_de"] is None


def test_pertamina_engineer_cannot_create_a_reading():
    _override("PERTAMINA_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={"condition_monitoring_schedule_code": "CMS-1", "asset_code": "G-201-01A"},
    )
    assert response.status_code == 403


def test_only_superuser_can_delete_a_reading():
    fake = _override("SUPERUSER")
    response = client.delete("/api/ltsa/condition-monitoring-readings/CMONR-1")
    assert response.status_code == 200
    assert fake.calls[0][0] == "soft_delete"


def test_tap_admin_cannot_delete_a_reading():
    _override("TAP_ADMIN")
    response = client.delete("/api/ltsa/condition-monitoring-readings/CMONR-1")
    assert response.status_code == 403


def test_anonymous_create_is_401():
    app.dependency_overrides.clear()
    response = client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={"condition_monitoring_schedule_code": "CMS-1", "asset_code": "G-201-01A"},
    )
    assert response.status_code == 401


def test_created_by_is_always_the_authenticated_actor():
    fake = _override("TAP_ENGINEER", user_id="real-actor")
    client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={"condition_monitoring_schedule_code": "CMS-1", "asset_code": "G-201-01A", "created_by": "spoofed"},
    )
    assert fake.calls[0][1]["created_by"] == "real-actor"


def test_john_crane_engineer_can_acknowledge_a_submitted_reading():
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/technical-review",
        json={"action": "ACKNOWLEDGE", "comment": "Within normal operating range"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "FINALIZED"


def test_john_crane_engineer_can_technically_approve():
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/technical-review",
        json={"action": "APPROVE", "recommendation": "Schedule seal replacement within 2 weeks"},
    )
    assert response.status_code == 200


def test_tap_engineer_cannot_technically_review():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/technical-review",
        json={"action": "ACKNOWLEDGE"},
    )
    assert response.status_code == 403


def test_pertamina_viewer_cannot_technically_review():
    _override("PERTAMINA_VIEWER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/technical-review",
        json={"action": "ACKNOWLEDGE"},
    )
    assert response.status_code == 403


def test_tap_admin_can_administratively_return_for_correction():
    _override("TAP_ADMIN")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/admin-review",
        json={"return_reason": "Reading date is missing"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "RETURNED_FOR_CORRECTION"


def test_submit_returns_409_for_an_unknown_reading():
    _override("TAP_ENGINEER", repository=FakeConditionMonitoringReadingRepository(existing_codes=()))
    response = client.post("/api/ltsa/condition-monitoring-readings/CMONR-MISSING/submit")
    assert response.status_code == 409


# MWO-LTSA-CMON-ADHOC-ENTRY-001 -- the ad-hoc (schedule-free) create
# route. Same FakeConditionMonitoringReadingRepository as every test
# above, only its new create_ad_hoc_draft() method is exercised here.

def _adhoc_payload(**overrides):
    payload = {
        "asset_code": "G-201-01A",
        "reading_date": "2026-09-06",
        "measurements": {"mechseal_temp_de": 75.2},
    }
    payload.update(overrides)
    return payload


def test_ad_hoc_endpoint_exists_and_succeeds_for_a_canonical_pump():
    fake = _override("TAP_ENGINEER")
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=_adhoc_payload())
    assert response.status_code == 200
    assert fake.calls[0][0] == "create_ad_hoc_draft"


def test_ad_hoc_requires_maintenance_write():
    _override("PERTAMINA_ENGINEER")
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=_adhoc_payload())
    assert response.status_code == 403


def test_ad_hoc_anonymous_is_401():
    app.dependency_overrides.clear()
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=_adhoc_payload())
    assert response.status_code == 401


def test_ad_hoc_actor_comes_from_authenticated_identity_not_request_body():
    fake = _override("TAP_ENGINEER", user_id="real-actor-99")
    # Even if a caller tries to smuggle an actor/created_by-shaped field
    # into the body, ConditionMonitoringReadingAdHocCreateRequest has no
    # such field at all -- FastAPI/Pydantic drops any unknown key.
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(created_by="attacker-supplied", actor="attacker-supplied"),
    )
    assert response.status_code == 200
    assert fake.calls[0][1]["created_by"] == "real-actor-99"


def test_ad_hoc_client_cannot_inject_code_provenance_or_status():
    fake = _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(
            condition_monitoring_reading_code="CMONR-FORGED",
            provenance="WHATSAPP",
            workflow_status="FINALIZED",
        ),
    )
    assert response.status_code == 200
    kwargs = fake.calls[0][1]
    # The request model has no such fields, so nothing forged reaches the
    # repository call -- provenance is always the router's own hardcoded
    # "MANUAL", never client-supplied.
    assert kwargs["provenance"] == "MANUAL"
    assert "condition_monitoring_reading_code" not in kwargs
    assert "workflow_status" not in kwargs


def test_ad_hoc_unknown_pump_is_404():
    _override("TAP_ENGINEER", repository=FakeConditionMonitoringReadingRepository(known_assets=()))
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=_adhoc_payload())
    assert response.status_code == 404


def test_ad_hoc_missing_reading_date_is_422():
    _override("TAP_ENGINEER")
    payload = _adhoc_payload()
    del payload["reading_date"]
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=payload)
    assert response.status_code == 422


def test_ad_hoc_never_requires_a_schedule_code():
    fake = _override("TAP_ENGINEER")
    payload = _adhoc_payload()
    assert "condition_monitoring_schedule_code" not in payload  # the request model has no such field
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=payload)
    assert response.status_code == 200
    assert "condition_monitoring_schedule_code" not in fake.calls[0][1]


def test_ad_hoc_provenance_is_always_manual():
    fake = _override("TAP_ENGINEER")
    client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=_adhoc_payload())
    assert fake.calls[0][1]["provenance"] == "MANUAL"


def test_ad_hoc_source_reference_is_self_disclosing_manual_web():
    fake = _override("TAP_ENGINEER")
    client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=_adhoc_payload())
    assert fake.calls[0][1]["source_reference"].startswith("MANUAL_WEB:")


def test_ad_hoc_creates_exactly_one_reading():
    fake = _override("TAP_ENGINEER")
    client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=_adhoc_payload())
    assert len(fake.calls) == 1
    assert fake.calls[0][0] == "create_ad_hoc_draft"


def test_ad_hoc_missing_measurement_is_null_not_zero():
    fake = _override("TAP_ENGINEER")
    client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(measurements={"mechseal_temp_de": 75.2}),
    )
    measurements = fake.calls[0][1]["measurements"]
    assert measurements["mechseal_temp_de"] == 75.2
    assert measurements["mechseal_temp_nde"] is None
    assert measurements["flushing_temp_de"] is None


def test_ad_hoc_explicit_zero_is_preserved_not_treated_as_blank():
    fake = _override("TAP_ENGINEER")
    client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(measurements={"suction_pressure": 0}),
    )
    measurements = fake.calls[0][1]["measurements"]
    assert measurements["suction_pressure"] == 0
    assert measurements["suction_pressure"] is not None


def test_ad_hoc_leak_tri_state_de_and_nde_independent():
    fake = _override("TAP_ENGINEER")
    client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(measurements={"mechanical_seal_leak_de": True, "mechanical_seal_leak_nde": False}),
    )
    measurements = fake.calls[0][1]["measurements"]
    assert measurements["mechanical_seal_leak_de"] is True
    assert measurements["mechanical_seal_leak_nde"] is False  # NULL != FALSE -- explicit False preserved


def test_ad_hoc_leak_not_recorded_stays_null_never_false():
    fake = _override("TAP_ENGINEER")
    client.post("/api/ltsa/condition-monitoring-readings/ad-hoc", json=_adhoc_payload(measurements={}))
    measurements = fake.calls[0][1]["measurements"]
    assert measurements["mechanical_seal_leak_de"] is None
    assert measurements["mechanical_seal_leak_nde"] is None


def test_ad_hoc_de_only_nde_only_and_both_independently_preserved():
    fake = _override("TAP_ENGINEER")

    client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(measurements={"mechseal_temp_de": 75.2}),
    )
    de_only = fake.calls[0][1]["measurements"]
    assert de_only["mechseal_temp_de"] == 75.2 and de_only["mechseal_temp_nde"] is None

    client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(measurements={"mechseal_temp_nde": 68.0}),
    )
    nde_only = fake.calls[1][1]["measurements"]
    assert nde_only["mechseal_temp_nde"] == 68.0 and nde_only["mechseal_temp_de"] is None

    client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(measurements={"mechseal_temp_de": 75.2, "mechseal_temp_nde": 68.0}),
    )
    both = fake.calls[2][1]["measurements"]
    assert both["mechseal_temp_de"] == 75.2 and both["mechseal_temp_nde"] == 68.0

    client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(measurements={}),
    )
    neither = fake.calls[3][1]["measurements"]
    assert neither["mechseal_temp_de"] is None and neither["mechseal_temp_nde"] is None


def test_ad_hoc_changing_de_does_not_mutate_nde_field_independence():
    fake = _override("TAP_ENGINEER")
    client.post(
        "/api/ltsa/condition-monitoring-readings/ad-hoc",
        json=_adhoc_payload(measurements={"flushing_temp_de": 40.0, "flushing_temp_nde": 39.5}),
    )
    measurements = fake.calls[0][1]["measurements"]
    # Both explicitly provided values are preserved independently -- one
    # was never overwritten or coerced by the other's presence.
    assert measurements["flushing_temp_de"] == 40.0
    assert measurements["flushing_temp_nde"] == 39.5


# MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- the atomic bulk ad-hoc route.

def _bulk_row(asset_code="G-201-01A", **overrides):
    row = {"asset_code": asset_code, "reading_date": "2026-09-06", "measurements": {"mechseal_temp_de": 75.2}}
    row.update(overrides)
    return row


def _bulk_payload(rows):
    return {"readings": rows}


def test_bulk_ad_hoc_endpoint_exists_and_requires_maintenance_write():
    _override("PERTAMINA_ENGINEER")
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload([_bulk_row()]))
    assert response.status_code == 403


def test_bulk_ad_hoc_anonymous_is_401():
    app.dependency_overrides.clear()
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload([_bulk_row()]))
    assert response.status_code == 401


def test_bulk_ad_hoc_empty_batch_is_422():
    _override("TAP_ENGINEER")
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload([]))
    assert response.status_code == 422


def test_bulk_ad_hoc_ten_rows_creates_exactly_ten():
    fake = _override("TAP_ENGINEER", repository=FakeConditionMonitoringReadingRepository(
        known_assets=[f"PUMP-{i}" for i in range(10)]
    ))
    rows = [_bulk_row(asset_code=f"PUMP-{i}", measurements={"mechseal_temp_de": float(i)}) for i in range(10)]
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload(rows))
    assert response.status_code == 200
    assert len(response.json()["data"]) == 10
    assert fake.calls[0][0] == "create_ad_hoc_batch"
    assert len(fake.calls[0][1]) == 10  # exactly one call to the repository, not ten


def test_bulk_ad_hoc_row_isolation_de_only_nde_only_both_zero_and_leak_tri_state():
    fake = _override("TAP_ENGINEER", repository=FakeConditionMonitoringReadingRepository(
        known_assets=["PUMP-A", "PUMP-B", "PUMP-C", "PUMP-D", "PUMP-E"]
    ))
    rows = [
        _bulk_row(asset_code="PUMP-A", measurements={"mechseal_temp_de": 75.2}),
        _bulk_row(asset_code="PUMP-B", measurements={"mechseal_temp_nde": 68.0}),
        _bulk_row(asset_code="PUMP-C", measurements={"mechseal_temp_de": 70.0, "mechseal_temp_nde": 65.0}),
        _bulk_row(asset_code="PUMP-D", measurements={"suction_pressure": 0}),
        _bulk_row(asset_code="PUMP-E", measurements={"mechanical_seal_leak_de": False, "mechanical_seal_leak_nde": None}),
    ]
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload(rows))
    assert response.status_code == 200
    sent_rows = fake.calls[0][1]

    a, b, c, d, e = (r["measurements"] for r in sent_rows)
    assert a["mechseal_temp_de"] == 75.2 and a["mechseal_temp_nde"] is None
    assert b["mechseal_temp_de"] is None and b["mechseal_temp_nde"] == 68.0
    assert c["mechseal_temp_de"] == 70.0 and c["mechseal_temp_nde"] == 65.0
    assert d["suction_pressure"] == 0 and d["suction_pressure"] is not None
    assert e["mechanical_seal_leak_de"] is False and e["mechanical_seal_leak_nde"] is None
    # Row isolation: PUMP-A's own edit never touched PUMP-B/C/D/E's fields.
    assert b["suction_pressure"] is None
    assert c["mechanical_seal_leak_de"] is None


def test_bulk_ad_hoc_unknown_pump_in_batch_rejected_with_409_no_partial_success():
    fake = _override("TAP_ENGINEER", repository=FakeConditionMonitoringReadingRepository(
        known_assets=["PUMP-GOOD"]
    ))
    rows = [_bulk_row(asset_code="PUMP-GOOD"), _bulk_row(asset_code="PUMP-UNKNOWN")]
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload(rows))
    assert response.status_code == 409
    # The fake raises before returning anything -- exactly mirroring the
    # real repository's precheck DO block raising inside the same
    # transaction the multi-row INSERT lives in, so nothing commits.
    assert fake.calls[0][0] == "create_ad_hoc_batch"


def test_bulk_ad_hoc_provenance_schedule_sentinel_and_actor_always_server_controlled():
    fake = _override("TAP_ENGINEER", user_id="real-actor-7", repository=FakeConditionMonitoringReadingRepository(
        known_assets=["PUMP-A", "PUMP-B"]
    ))
    rows = [_bulk_row(asset_code="PUMP-A"), _bulk_row(asset_code="PUMP-B")]
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload(rows))
    assert response.status_code == 200
    _, sent_rows, kwargs = fake.calls[0]
    assert kwargs["created_by"] == "real-actor-7"
    for row in sent_rows:
        # No per-row field can carry provenance/reading_code/workflow_status/
        # actor -- the request model has none of them.
        assert "provenance" not in row
        assert "condition_monitoring_reading_code" not in row
        assert "workflow_status" not in row
        assert row["source_reference"].startswith("MANUAL_WEB:")
    # Each row gets its own, distinct source_reference -- never reused
    # across rows in the same batch.
    assert len({row["source_reference"] for row in sent_rows}) == len(sent_rows)


# MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001, Section 13 -- simulated failure/
# retry at the router-contract level: a Fake cannot itself prove real
# Postgres transaction atomicity (that proof requires a real database --
# see test_condition_monitoring_reading_bulk_atomicity_real_db.py,
# written this phase but NOT executable in this environment: Docker
# Desktop was unavailable throughout this session, confirmed via `docker
# ps` failing with "failed to connect to the docker API"). What IS
# proven here, at the contract level: a repository-raised failure never
# yields a 200/partial-success response, and a corrected retry succeeds
# cleanly afterward with fresh, non-duplicate codes.
def test_bulk_ad_hoc_simulated_persistence_failure_yields_no_success_response():
    fake = _override("TAP_ENGINEER", repository=FakeConditionMonitoringReadingRepository(
        known_assets=[f"PUMP-{i}" for i in range(10)],
        bulk_failure=RuntimeError("simulated persistence failure mid-transaction"),
    ))
    rows = [_bulk_row(asset_code=f"PUMP-{i}") for i in range(10)]
    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload(rows))
    assert response.status_code == 409
    assert "data" not in response.json() or not response.json().get("data")


def test_bulk_ad_hoc_corrected_retry_after_failure_creates_all_ten_with_unique_codes():
    fake = FakeConditionMonitoringReadingRepository(known_assets=[f"PUMP-{i}" for i in range(10)])
    _override("TAP_ENGINEER", repository=fake)
    rows = [_bulk_row(asset_code=f"PUMP-{i}") for i in range(10)]

    response = client.post("/api/ltsa/condition-monitoring-readings/ad-hoc/bulk", json=_bulk_payload(rows))

    assert response.status_code == 200
    created = response.json()["data"]
    assert len(created) == 10
    codes = [row["condition_monitoring_reading_code"] for row in created]
    assert len(set(codes)) == 10  # all unique, no duplicate code

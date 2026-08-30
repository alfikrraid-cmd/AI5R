import hashlib
import hmac
import json
import sys
from pathlib import Path

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pytest
from fastapi.testclient import TestClient

from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity
from API.whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier
from API.whatsapp_outbound_client import OutboundResult
from dependencies import (
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_reading_repository,
    get_copilot_ai_client,
    get_equipment_timeline_service,
    get_fleet_executive_summary_service,
    get_installation_gateway,
    get_installation_report_repository,
    get_ltsa_ai_condition_monitoring_reading_repository,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_mechanical_seal_stock_repository,
    get_pm_occurrence_repository,
    get_pump_gateway,
    get_whatsapp_intake_repository,
    get_whatsapp_outbound_client,
    get_work_order_gateway,
)
from main import app

client = TestClient(app)

WEBHOOK_PATH = "/api/ltsa/whatsapp/webhook"
_UNSET = object()


class FakePumpGateway:
    def __init__(self):
        self.pumps = {
            "211-P-13AR": {"tag_number": "211-P-13AR", "area": "HOC"},
            "210-P-05AR": {"tag_number": "210-P-05AR", "area": "HOC"},
        }

    def get_pump(self, tag_number):
        pump = self.pumps.get(tag_number)
        return {"success": bool(pump), "data": pump}


class FakeConditionMonitoringReadingRepository:
    def __init__(self, pumps=None, schedules=None, fail=False):
        self.pumps = pumps if pumps is not None else {"211-P-13AR", "210-P-05AR"}
        self.schedules = schedules if schedules is not None else []
        self.rows = []
        self._seq = 0
        self.fail = fail
        self.create_draft_calls = []
        self.create_ad_hoc_draft_calls = []

    def find_by_source_reference(self, source_reference):
        for row in self.rows:
            if row.get("source_reference") == source_reference:
                return row
        return None

    def find_open_schedules_by_asset(self, asset_code):
        return [
            dict(s) for s in self.schedules if s["asset_code"] == asset_code and s["status"] not in {"CANCELLED", "COMPLETED"}
        ]

    def _new_row(self, *, schedule_code, asset_code, asset_type, reading_date, measurements, created_by, provenance, source_reference, finding):
        self._seq += 1
        row = {
            "condition_monitoring_reading_code": f"CMONR-TEST{self._seq:04d}",
            "condition_monitoring_schedule_code": schedule_code,
            "asset_code": asset_code,
            "asset_type": asset_type,
            "reading_date": reading_date,
            "measurements": dict(measurements),
            "created_by": created_by,
            "provenance": provenance,
            "source_reference": source_reference,
            "finding": finding,
            "workflow_status": "DRAFT",
        }
        self.rows.append(row)
        return row

    def create_draft(self, *, condition_monitoring_schedule_code, asset_code, asset_type, reading_date, measurements, created_by, provenance, source_reference, finding):
        self.create_draft_calls.append(condition_monitoring_schedule_code)
        if self.fail:
            raise RuntimeError("simulated write failure")
        schedule = next(
            (s for s in self.schedules if s["condition_monitoring_schedule_code"] == condition_monitoring_schedule_code),
            None,
        )
        if schedule is None or asset_code not in self.pumps:
            # Mirrors the real repository's own WHERE EXISTS-no-match
            # behavior (raises IndexError on rows[0] of an empty list).
            raise IndexError("list index out of range")
        row = self._new_row(
            schedule_code=condition_monitoring_schedule_code, asset_code=asset_code, asset_type=asset_type,
            reading_date=reading_date, measurements=measurements, created_by=created_by,
            provenance=provenance, source_reference=source_reference, finding=finding,
        )
        schedule["status"] = "COMPLETED"
        return row

    def create_ad_hoc_draft(self, *, asset_code, asset_type, reading_date, measurements, created_by, source_reference, finding, provenance):
        self.create_ad_hoc_draft_calls.append(source_reference)
        if self.fail:
            raise RuntimeError("simulated write failure")
        if asset_code not in self.pumps:
            return None
        return self._new_row(
            schedule_code=f"UNSCHEDULED::{provenance}", asset_code=asset_code, asset_type=asset_type,
            reading_date=reading_date, measurements=measurements, created_by=created_by,
            provenance=provenance, source_reference=source_reference, finding=finding,
        )


class FakePMOccurrenceRepository:
    def __init__(self, pumps=None, schedules=None, fail=False):
        self.pumps = pumps if pumps is not None else {"211-P-13AR", "210-P-05AR"}
        self.schedules = schedules if schedules is not None else []
        self.rows = []
        self._seq = 0
        self.fail = fail
        self.create_draft_calls = []
        self.create_ad_hoc_draft_calls = []

    def find_by_source_reference(self, source_reference):
        for row in self.rows:
            if row.get("source_reference") == source_reference:
                return row
        return None

    def find_open_schedules_by_asset(self, asset_code):
        return [
            dict(s) for s in self.schedules if s["asset_code"] == asset_code and s["status"] not in {"CANCELLED", "COMPLETED"}
        ]

    def _new_row(self, *, schedule_code, asset_code, asset_type, occurrence_date, activities, remarks, created_by, provenance, source_reference):
        self._seq += 1
        row = {
            "pm_occurrence_code": f"PMOCC-TEST{self._seq:04d}",
            "pm_schedule_code": schedule_code,
            "asset_code": asset_code,
            "asset_type": asset_type,
            "occurrence_date": occurrence_date,
            "activities": activities,
            "remarks": remarks,
            "created_by": created_by,
            "provenance": provenance,
            "source_reference": source_reference,
            "workflow_status": "DRAFT",
        }
        self.rows.append(row)
        return row

    def create_draft(self, *, pm_schedule_code, asset_code, asset_type, occurrence_date, activities, remarks, created_by, provenance, source_reference):
        self.create_draft_calls.append(pm_schedule_code)
        if self.fail:
            raise RuntimeError("simulated write failure")
        schedule = next(
            (s for s in self.schedules if s["pm_schedule_code"] == pm_schedule_code),
            None,
        )
        if schedule is None or asset_code not in self.pumps:
            # Mirrors the real repository's own WHERE EXISTS-no-match
            # behavior (raises IndexError on rows[0] of an empty list).
            raise IndexError("list index out of range")
        row = self._new_row(
            schedule_code=pm_schedule_code, asset_code=asset_code, asset_type=asset_type,
            occurrence_date=occurrence_date, activities=activities, remarks=remarks, created_by=created_by,
            provenance=provenance, source_reference=source_reference,
        )
        schedule["status"] = "COMPLETED"
        return row

    def create_ad_hoc_draft(self, *, asset_code, asset_type, occurrence_date, activities, remarks, created_by, source_reference, provenance):
        self.create_ad_hoc_draft_calls.append(source_reference)
        if self.fail:
            raise RuntimeError("simulated write failure")
        if asset_code not in self.pumps:
            return None
        return self._new_row(
            schedule_code=f"UNSCHEDULED::{provenance}", asset_code=asset_code, asset_type=asset_type,
            occurrence_date=occurrence_date, activities=activities, remarks=remarks, created_by=created_by,
            provenance=provenance, source_reference=source_reference,
        )


class FakeIntakeRepository:
    def __init__(self, identities=None):
        # identities: dict[normalized_phone_number, AuthenticatedIdentity]
        self.identities = identities or {}
        self.rows = []
        self._seq = 0
        self.transition_calls = 0

    def find_identity_by_sender_hash(self, sender_hash):
        for phone, identity in self.identities.items():
            if sender_hash == hash_sender_identifier(normalize_sender_identifier(phone)):
                return identity
        return None

    def find_pending_by_delivery_key(self, provider, provider_message_id, sender_user_id):
        for row in self.rows:
            if (
                row["provider"] == provider
                and row["provider_message_id"] == provider_message_id
                and row["sender_user_id"] == sender_user_id
            ):
                return row
        return None

    def find_pending_by_confirmation_id(self, confirmation_id, sender_user_id):
        for row in self.rows:
            if row["confirmation_id"] == confirmation_id and row["sender_user_id"] == sender_user_id:
                return row
        return None

    def find_latest_actionable_pending(self, sender_user_id):
        candidates = self.find_actionable_pending_list(sender_user_id)
        return candidates[0] if candidates else None

    def find_actionable_pending_list(self, sender_user_id):
        # Production regression fix -- CONFIRMED excluded from candidate
        # discovery (matches the real repository's corrected SQL).
        open_states = {"READY_FOR_CONFIRMATION", "NEEDS_INFORMATION"}
        rows = [r for r in self.rows if r["sender_user_id"] == sender_user_id and r["state"] in open_states]
        return list(reversed(rows))

    def find_pending_by_outbound_message_id(self, provider_message_id, sender_user_id):
        for row in self.rows:
            if (
                row.get("last_outbound_provider_message_id") == provider_message_id
                and row["sender_user_id"] == sender_user_id
            ):
                return row
        return None

    def create_pending(self, payload):
        self._seq += 1
        row = {
            "intake_id": f"wa-{self._seq}",
            # Matches the real shape exactly (migration 030's confirmation_id
            # DEFAULT: 'WA-CONF-' + 32 lowercase hex chars) -- required now
            # that _CONFIRMATION_CODE_PATTERN strictly requires exactly 32
            # hex characters; a shorter sequential id would never match.
            "confirmation_id": f"WA-CONF-{self._seq:032x}",
            "reply_text": payload.get("reply"),
            "last_outbound_provider_message_id": None,
            **payload,
        }
        self.rows.append(row)
        return row

    def transition_pending(
        self,
        intake_id,
        *,
        state,
        confirmed_by=None,
        validation_result=None,
        structured_payload=None,
        last_outbound_provider_message_id=None,
    ):
        self.transition_calls += 1
        for row in self.rows:
            if row["intake_id"] == intake_id:
                row["state"] = state
                if confirmed_by is not None and state == "CONFIRMED":
                    row["confirmed_by"] = confirmed_by
                if validation_result is not None:
                    row["validation_result"] = validation_result
                if structured_payload is not None:
                    row["structured_payload"] = structured_payload
                if last_outbound_provider_message_id is not None:
                    row["last_outbound_provider_message_id"] = last_outbound_provider_message_id
                return row
        raise AssertionError(f"no such pending row: {intake_id}")


class FakeOutboundClient:
    def __init__(self, *, raises: bool = False):
        self.calls: list[tuple[str, str]] = []
        self._raises = raises
        self._sent = 0

    def send_text(self, recipient, text):
        self.calls.append((recipient, text))
        if self._raises:
            raise RuntimeError("simulated provider failure")
        self._sent += 1
        # A unique id per call -- matches real Meta behavior (every send
        # gets its own message id) and avoids accidental collisions
        # between rows in multi-pending tests.
        return OutboundResult(status="SUCCESS", http_status=200, provider_message_id=f"wamid.OUT{self._sent}")


SENDER_A = "+15550000001"
SENDER_B = "+15550000002"


def _identity(user_id="user-1", organization_id="org-tap", organization_code="TAP", role="TAP_ENGINEER", **overrides):
    defaults = dict(
        user_id=user_id,
        email=None,
        username="field.operator",
        organization_id=organization_id,
        organization_code=organization_code,
        role=role,
        permissions=ROLE_PERMISSIONS[role],
        data_scope_type=None,
        data_scope_value=None,
    )
    defaults.update(overrides)
    return AuthenticatedIdentity(**defaults)


def _out_of_scope_identity(**overrides):
    # PERTAMINA_ENGINEER is a scoped role (unlike TAP_ENGINEER); pinned to
    # area HSC while every FakePumpGateway pump lives in area HOC.
    return _identity(
        role="PERTAMINA_ENGINEER",
        data_scope_type="AREA",
        data_scope_value="HSC",
        **overrides,
    )


@pytest.fixture(autouse=True)
def clear_overrides(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.delenv("WHATSAPP_VERIFY_TOKEN", raising=False)
    monkeypatch.delenv("META_APP_SECRET", raising=False)
    yield
    app.dependency_overrides.clear()


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _message_envelope(
    *,
    message_id="wamid.1",
    sender="15550000001",
    text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor",
    context_id=None,
):
    message = {
        "from": sender,
        "id": message_id,
        "timestamp": "1700000000",
        "type": "text",
        "text": {"body": text},
    }
    if context_id:
        message["context"] = {"id": context_id}
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "123456"},
                            "messages": [message],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _status_envelope():
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "123456"},
                            "statuses": [
                                {"id": "wamid.status1", "status": "delivered", "timestamp": "1700000001", "recipient_id": "15550000001"}
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _unknown_envelope():
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {"id": "WABA_ID", "changes": [{"value": {"messaging_product": "whatsapp"}, "field": "account_alerts"}]}
        ],
    }


def _post(body: dict) -> "TestClient.__enter__.__self__":
    raw = json.dumps(body).encode("utf-8")
    return client.post(WEBHOOK_PATH, content=raw, headers={"X-Hub-Signature-256": _sign(raw, "test-app-secret")})


class _InertLTSAAIGateway:
    # Safe stand-in for every LTSA AI query gateway/service/repository --
    # ANY method call returns a uniform {"success": False} shape, matching
    # every copilot_ask_service.py handler's own "data unavailable ->
    # DATA_GAP" branch. Used as the default for all nine LTSA AI query
    # dependencies so a pre-existing test whose message text happens to
    # match copilot_ask_service's OWN intent classifier (e.g. containing
    # "WO"/"PM"-adjacent words) can never accidentally reach a real
    # gateway/DB, and never crashes -- it just gets a DATA_GAP answer
    # exactly like a real "nothing found" response would produce.
    def __getattr__(self, _name):
        def _stub(*_args, **_kwargs):
            return {"success": False, "data": None}
        return _stub


def _default_ltsa_ai_query_deps():
    from API.whatsapp_intake_service import LTSAAIQueryDependencies
    return LTSAAIQueryDependencies(
        ai_client=None,
        maintenance_history_gateway=_InertLTSAAIGateway(),
        work_order_gateway=_InertLTSAAIGateway(),
        installation_gateway=_InertLTSAAIGateway(),
        ltsa_knowledge_service=_InertLTSAAIGateway(),
        equipment_timeline_service=_InertLTSAAIGateway(),
        condition_monitoring_reading_gateway=_InertLTSAAIGateway(),
        installation_report_repository=_InertLTSAAIGateway(),
        mechanical_seal_stock_repository=_InertLTSAAIGateway(),
        # Safe against BOTH crash modes: _handle_condition_monitoring
        # rejects a non-list result (the inert stub's own {"success":
        # False} shape) as DATA_GAP, and _handle_fleet_priority uses
        # getattr(..., "top_risks", None) rather than assuming an
        # attribute exists -- proven directly in copilot_ask_service's
        # own test suite, not just asserted here.
        condition_monitoring_reading_repository=_InertLTSAAIGateway(),
        fleet_executive_summary_service=_InertLTSAAIGateway(),
    )


def _wire(
    monkeypatch, repo, outbound=None, pump_gateway=None, cmon_repository=_UNSET, pm_repository=_UNSET,
    ltsa_ai_query_deps=_UNSET,
):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: (pump_gateway or FakePumpGateway())
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: (outbound or FakeOutboundClient())
    # Defaults to None (no authoritative CMON/PM writer available),
    # matching every pre-existing test's expectation of the prior "draft
    # intake, no PM/CMON record" behavior -- only tests that explicitly
    # pass a cmon_repository/pm_repository opt into the authoritative-
    # write path. Also overrides the REAL production dependency so no
    # test can accidentally reach a real DB connection attempt.
    resolved_cmon = None if cmon_repository is _UNSET else cmon_repository
    app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: resolved_cmon
    resolved_pm = None if pm_repository is _UNSET else pm_repository
    app.dependency_overrides[get_pm_occurrence_repository] = lambda: resolved_pm
    # LTSA AI query dependencies -- defaults to the inert/no-AI-client
    # bundle above so no pre-existing test can accidentally reach a real
    # gateway or LLM provider; a test exercising the query path passes an
    # explicit LTSAAIQueryDependencies (see _fake_ltsa_ai_query_deps below).
    deps = _default_ltsa_ai_query_deps() if ltsa_ai_query_deps is _UNSET else ltsa_ai_query_deps
    app.dependency_overrides[get_copilot_ai_client] = lambda: deps.ai_client
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: deps.maintenance_history_gateway
    app.dependency_overrides[get_work_order_gateway] = lambda: deps.work_order_gateway
    app.dependency_overrides[get_installation_gateway] = lambda: deps.installation_gateway
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: deps.ltsa_knowledge_service
    app.dependency_overrides[get_equipment_timeline_service] = lambda: deps.equipment_timeline_service
    app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: deps.condition_monitoring_reading_gateway
    app.dependency_overrides[get_installation_report_repository] = lambda: deps.installation_report_repository
    app.dependency_overrides[get_mechanical_seal_stock_repository] = lambda: deps.mechanical_seal_stock_repository
    # Distinct callable from get_condition_monitoring_reading_repository
    # (overridden separately above via resolved_cmon) -- see
    # dependencies.py's get_ltsa_ai_condition_monitoring_reading_
    # repository docstring for why the write and query roles need
    # independent test overrides despite sharing one production singleton.
    app.dependency_overrides[get_ltsa_ai_condition_monitoring_reading_repository] = lambda: deps.condition_monitoring_reading_repository
    app.dependency_overrides[get_fleet_executive_summary_service] = lambda: deps.fleet_executive_summary_service
    return outbound


# --- GET verification -------------------------------------------------


def test_get_valid_verification_returns_exact_challenge(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
    response = client.get(
        WEBHOOK_PATH,
        params={"hub.mode": "subscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "challenge-12345"},
    )
    assert response.status_code == 200
    assert response.text == "challenge-12345"


def test_get_wrong_token_rejected(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
    response = client.get(
        WEBHOOK_PATH,
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong-token", "hub.challenge": "challenge-12345"},
    )
    assert response.status_code == 403


def test_get_missing_token_rejected(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
    response = client.get(WEBHOOK_PATH, params={"hub.mode": "subscribe", "hub.challenge": "challenge-12345"})
    assert response.status_code == 403


def test_get_wrong_mode_rejected(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
    response = client.get(
        WEBHOOK_PATH,
        params={"hub.mode": "unsubscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "challenge-12345"},
    )
    assert response.status_code == 403


def test_get_fails_closed_when_verify_token_not_configured():
    response = client.get(
        WEBHOOK_PATH,
        params={"hub.mode": "subscribe", "hub.verify_token": "anything", "hub.challenge": "challenge-12345"},
    )
    assert response.status_code == 403


# --- POST signature security -------------------------------------------


def test_post_valid_signature_accepted(monkeypatch):
    _wire(monkeypatch, FakeIntakeRepository({SENDER_A: _identity()}))
    response = _post(_message_envelope())
    assert response.status_code == 200


def test_post_invalid_signature_rejected(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "wrong-secret")})
    assert response.status_code == 403


def test_post_missing_signature_rejected(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(WEBHOOK_PATH, content=body)
    assert response.status_code == 403


def test_post_fails_closed_when_app_secret_not_configured():
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "any-secret")})
    assert response.status_code == 403


def test_post_invalid_signature_never_reaches_outbound(monkeypatch):
    outbound = FakeOutboundClient()
    _wire(monkeypatch, FakeIntakeRepository({SENDER_A: _identity()}), outbound)
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "wrong-secret")})
    assert response.status_code == 403
    assert outbound.calls == []


# --- basic payload routing (test 15: existing normal-flow regression) ----


def test_post_inbound_message_reaches_existing_intake_path(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    response = _post(_message_envelope(message_id="wamid.inbound1"))
    assert response.status_code == 200
    assert len(repo.rows) == 1
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    assert repo.rows[0]["detected_domain"] == "CONDITION_MONITORING"
    assert repo.rows[0]["organization_id"] == "org-tap"
    assert len(outbound.calls) == 1
    assert outbound.calls[0] == (SENDER_A, repo.rows[0]["reply_text"])


def test_post_status_callback_causes_no_engineering_write(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    response = _post(_status_envelope())
    assert response.status_code == 200
    assert response.json()["results"] == [{"status": "STATUS_ACKNOWLEDGED"}]
    assert repo.rows == []
    assert outbound.calls == []


def test_post_unknown_event_safely_handled(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    response = _post(_unknown_envelope())
    assert response.status_code == 200
    assert response.json()["results"] == [{"status": "UNKNOWN_EVENT_ACKNOWLEDGED"}]
    assert repo.rows == []
    assert outbound.calls == []


def test_post_duplicate_delivery_does_not_create_duplicate_pending_intake(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    body = json.dumps(_message_envelope(message_id="wamid.dup1")).encode("utf-8")
    signature = {"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    first = client.post(WEBHOOK_PATH, content=body, headers=signature)
    second = client.post(WEBHOOK_PATH, content=body, headers=signature)
    assert first.status_code == 200
    assert second.status_code == 200
    assert len(repo.rows) == 1
    assert len(outbound.calls) == 1


def test_post_unknown_sender_receives_the_existing_safe_reply_outbound(monkeypatch):
    repo = FakeIntakeRepository({})  # SENDER_A not registered
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    response = _post(_message_envelope(message_id="wamid.unknown1"))
    assert response.status_code == 200
    assert repo.rows == []
    assert outbound.calls == [(SENDER_A, "Nomor WhatsApp belum terdaftar.")]


def test_outbound_provider_failure_does_not_break_webhook_ack(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient(raises=True)
    _wire(monkeypatch, repo, outbound)
    response = _post(_message_envelope(message_id="wamid.outboundfail1"))
    assert response.status_code == 200
    assert len(repo.rows) == 1
    assert len(outbound.calls) == 1


def test_no_raw_phone_or_secret_in_logs(monkeypatch, caplog):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    with caplog.at_level("INFO"):
        response = _post(_message_envelope(message_id="wamid.privacy1"))
    assert response.status_code == 200
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "15550000001" not in log_text
    assert "+15550000001" not in log_text
    assert "test-app-secret" not in log_text
    assert "user-1" not in log_text  # raw user UUID must never appear either


# --- MWO-025J2 Part A: CONFIRMED must mean valid --------------------------


def test_missing_reading_date_stays_needs_information(monkeypatch):
    # Test 1: the 025F example message has no "hari ini" -> READING_DATE_
    # REQUIRED -> NEEDS_INFORMATION, with the intake engine's existing
    # follow-up question.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    response = _post(
        _message_envelope(message_id="wamid.needsinfo1", text="CMON 211-P-13AR: ditemukan kebocoran mechanical seal.")
    )
    assert response.status_code == 200
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"
    assert outbound.calls[-1] == (SENDER_A, "Reading date belum ada. Gunakan hari ini?")


def test_ya_answering_date_question_assigns_asia_jakarta_date_and_confirms(monkeypatch):
    # Tests 2 + 3: "YA" answering "Gunakan hari ini?" assigns today's date
    # in Asia/Jakarta, re-validates, and (since that was the only missing
    # piece) reaches CONFIRMED.
    from datetime import datetime, timedelta, timezone

    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.datequestion1", text="CMON 211-P-13AR: ditemukan kebocoran mechanical seal."))
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"

    response = _post(_message_envelope(message_id="wamid.ya1", text="YA"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"
    expected_today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    assert repo.rows[0]["structured_payload"]["reading_date"] == expected_today
    assert repo.rows[0]["validation_result"]["valid"] is True
    assert outbound.calls[-1] == (SENDER_A, "Terkonfirmasi sebagai draft intake. Belum dibuat record PM/CMON.")


def test_ya_still_invalid_after_date_fix_stays_needs_information(monkeypatch):
    # Test 4: pump tag missing entirely -> even after the date question is
    # answered "YA", PUMP_TAG_REQUIRED still blocks confirmation; state
    # stays NEEDS_INFORMATION and the reply asks for the remaining problem
    # only, not a generic re-ask of the date question already answered.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.notag1", text="CMON ditemukan kebocoran mechanical seal."))
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"
    assert "PUMP_TAG_REQUIRED" in repo.rows[0]["validation_result"]["errors"]

    response = _post(_message_envelope(message_id="wamid.ya_notag1", text="YA"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"
    assert outbound.calls[-1] == (SENDER_A, "Kode pump tidak ditemukan. Kirim tag pump yang tepat.")


# --- MWO-025J2 Part C: MA/area authorization -------------------------------


def test_registered_in_scope_sender_allowed(monkeypatch):
    # Test 5.
    repo = FakeIntakeRepository({SENDER_A: _identity()})  # TAP_ENGINEER: unrestricted
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    response = _post(_message_envelope(message_id="wamid.inscope1"))
    assert response.status_code == 200
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    assert "PUMP_OUT_OF_SCOPE" not in repo.rows[0]["validation_result"]["errors"]


def test_registered_out_of_scope_sender_denied_before_confirmed(monkeypatch):
    # Tests 6 + 7: scope is enforced at original intake AND rechecked at
    # "YA" time -- the same PERTAMINA_ENGINEER/HSC identity is used for
    # both messages (freshly re-resolved each time, never cached), and
    # confirmation must never be reached for an out-of-scope asset.
    repo = FakeIntakeRepository({SENDER_A: _out_of_scope_identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.oos1", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    assert "PUMP_OUT_OF_SCOPE" in repo.rows[0]["validation_result"]["errors"]
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"

    response = _post(_message_envelope(message_id="wamid.oos_ya1", text="YA"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] != "CONFIRMED"
    assert "PUMP_OUT_OF_SCOPE" in repo.rows[0]["validation_result"]["errors"]
    assert outbound.calls[-1] == (SENDER_A, "Pump di luar scope akun Anda.")


# --- MWO-025J2 Part D: org binding -----------------------------------------


def test_cross_org_confirmation_impossible(monkeypatch):
    # Test 9: a pending row bound to a different organization_id than the
    # confirming identity's currently-resolved org must never be
    # confirmable, even though sender_user_id matches (simulates a
    # multi-org user whose resolved membership changed between messages).
    repo = FakeIntakeRepository({SENDER_A: _identity(organization_id="org-tap")})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.crossorg1", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    repo.rows[0]["organization_id"] = "org-other"  # simulate a stored row from a different org

    response = _post(_message_envelope(message_id="wamid.crossorg_ya1", text="YA"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] != "CONFIRMED"
    assert outbound.calls[-1] == (SENDER_A, "Data tidak ditemukan.")


# --- MWO-025J2 Part B/cross-user -------------------------------------------


def test_cross_user_confirmation_impossible(monkeypatch):
    # Test 8: user B's "YA" must never confirm user A's pending row.
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id="user-a"), SENDER_B: _identity(user_id="user-b")})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.usera1", sender="15550000001", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"

    response = _post(_message_envelope(message_id="wamid.userb_ya1", sender="15550000002", text="YA"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"  # untouched
    assert outbound.calls[-1] == (SENDER_B, "Tidak ada data yang menunggu konfirmasi.")


# --- MWO-025J2 Part E: conversation correlation ----------------------------


def test_context_linked_ya_selects_exact_pending(monkeypatch):
    # Test 10: two actionable pending rows exist; a context-linked "YA"
    # (Meta context.id referencing AI5R's own prior outbound message for
    # the SECOND one) must confirm exactly that one, not "the latest."
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.rowA", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    _post(_message_envelope(message_id="wamid.rowB", text="CM 210-P-05AR hari ini DE 70 NDE 71 tidak bocor"))
    assert len(repo.rows) == 2
    row1_id = repo.rows[0]["intake_id"]
    # The webhook already persisted each row's own creation-reply message
    # id automatically (real behavior, exercised through the actual code
    # path, not hand-set) -- row 1 and row 2 have DISTINCT ids since
    # FakeOutboundClient assigns a fresh one per call.
    row1_outbound_id = repo.rows[0]["last_outbound_provider_message_id"]
    row2_outbound_id = repo.rows[1]["last_outbound_provider_message_id"]
    assert row1_outbound_id is not None and row1_outbound_id != row2_outbound_id

    response = _post(_message_envelope(message_id="wamid.contextya1", text="YA", context_id=row1_outbound_id))

    assert response.status_code == 200
    confirmed = [row for row in repo.rows if row["intake_id"] == row1_id][0]
    other = [row for row in repo.rows if row["intake_id"] != row1_id][0]
    assert confirmed["state"] == "CONFIRMED"
    assert other["state"] != "CONFIRMED"


def test_ambiguous_plain_ya_does_not_guess_or_confirm(monkeypatch):
    # Test 11: two actionable pending rows, plain unlinked "YA" -> neither
    # is touched; user is asked to clarify instead.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.ambigA", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    _post(_message_envelope(message_id="wamid.ambigB", text="CM 210-P-05AR hari ini DE 70 NDE 71 tidak bocor"))
    states_before = [row["state"] for row in repo.rows]

    response = _post(_message_envelope(message_id="wamid.ambig_ya1", text="YA"))

    assert response.status_code == 200
    assert [row["state"] for row in repo.rows] == states_before  # nothing confirmed, nothing changed
    assert "WA-CONF-" in outbound.calls[-1][1]


def test_explicit_confirmation_code_selector_resolves_ambiguity(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.selA", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    _post(_message_envelope(message_id="wamid.selB", text="CM 210-P-05AR hari ini DE 70 NDE 71 tidak bocor"))
    target_code = repo.rows[1]["confirmation_id"]

    response = _post(_message_envelope(message_id="wamid.sel_ya1", text=f"YA {target_code}"))

    assert response.status_code == 200
    assert repo.rows[1]["state"] == "CONFIRMED"
    assert repo.rows[0]["state"] != "CONFIRMED"


# --- MWO-025J2 Part F: idempotency ------------------------------------------


def test_repeated_ya_does_not_re_transition_or_re_confirm(monkeypatch):
    # Test 12.
    #
    # Production regression fix, semantic update: a plain, unlinked "YA"
    # no longer treats CONFIRMED rows as candidates at all (that's the
    # whole point of this fix -- see the "production regression fix"
    # section below), so with nothing else open, the repeat correctly
    # falls to the existing NO_PENDING_CONFIRMATION reply rather than
    # DUPLICATE_CONFIRMATION -- DUPLICATE_CONFIRMATION is still reachable,
    # unchanged, via an explicit reference (see
    # test_confirmed_code_repeat_via_explicit_selector_does_not_re_transition).
    # What this test still proves, and must keep proving: no re-transition,
    # no re-stamped confirmed_by/confirmed_at, on repeat -- the guarantee
    # in this test's name -- regardless of which reply text results.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.repeat1", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    _post(_message_envelope(message_id="wamid.repeat_ya1", text="YA"))
    confirmed_at_first = repo.rows[0].get("confirmed_by")
    assert repo.rows[0]["state"] == "CONFIRMED"

    response = _post(_message_envelope(message_id="wamid.repeat_ya2", text="YA"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert repo.rows[0].get("confirmed_by") == confirmed_at_first
    assert outbound.calls[-1] == (SENDER_A, "Tidak ada data yang menunggu konfirmasi.")


# --- structural guard: no authoritative engineering write (test 16) -------


def test_confirmation_flow_never_touches_authoritative_tables(monkeypatch):
    # FakeIntakeRepository above exposes no create/write method for
    # condition_monitoring_reading, pm_occurrence, cm_report, or
    # work_order at all -- there is structurally no way for this flow to
    # call one. This test proves the full NEEDS_INFORMATION -> YA ->
    # CONFIRMED path completes without error against that repository,
    # confirming no such call is attempted anywhere in the path.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.noauth1", text="CMON 211-P-13AR: ditemukan kebocoran mechanical seal."))
    response = _post(_message_envelope(message_id="wamid.noauth_ya1", text="YA"))
    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"


# --- Confirmation integrity fix: real production defect reproduction ------
#
# A real WhatsApp interaction produced FOUR simultaneous WA-CONF pending
# rows for the same (CONDITION_MONITORING, 211-P-13AR) intent, and then
# "Kode konfirmasi tidak ditemukan." when the user replied with a code
# copied verbatim from AI5R's own displayed listing (which includes a
# trailing ": CONDITION_MONITORING 211-P-13AR" label). Two separate root
# causes, reproduced individually below.


def test_create_confirmation_then_retrieve_by_exact_generated_code(monkeypatch):
    # TEST 1.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.gencode1", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    generated_code = repo.rows[0]["confirmation_id"]

    found = repo.find_pending_by_confirmation_id(generated_code, "user-1")

    assert found is not None
    assert found["intake_id"] == repo.rows[0]["intake_id"]


def test_ya_with_confirmation_code_and_trailing_descriptive_label_resolves(monkeypatch):
    # TEST 3 -- reproduces the exact real defect: the user replied with
    # AI5R's own displayed line verbatim, "Ya WA-CONF-<id>:
    # CONDITION_MONITORING 211-P-13AR", copied straight from the
    # ambiguity listing. Before the fix, the naive "everything after the
    # first space" selector included the trailing ": CONDITION_MONITORING
    # 211-P-13AR" text, so the exact-match confirmation_id lookup always
    # failed with "Kode konfirmasi tidak ditemukan." -- reproduced here
    # with two ambiguous rows exactly like the real conversation.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.labelA", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    _post(_message_envelope(message_id="wamid.labelB", text="CM 210-P-05AR hari ini DE 70 NDE 71 tidak bocor"))
    target_code = repo.rows[0]["confirmation_id"]

    response = _post(
        _message_envelope(
            message_id="wamid.label_ya1",
            text=f"Ya {target_code}: CONDITION_MONITORING 211-P-13AR",
        )
    )

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert repo.rows[1]["state"] != "CONFIRMED"
    assert outbound.calls[-1] != (SENDER_A, "Kode konfirmasi tidak ditemukan.")


def test_ya_with_unrecognizable_trailing_text_falls_back_instead_of_rejecting(monkeypatch):
    # A related edge case the same fix resolves: trailing text that was
    # never meant to be a code (no "WA-CONF-" anywhere in it) must not be
    # treated as an unrecognized-code rejection -- it falls through to the
    # normal single-candidate resolution.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.plain1", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))

    response = _post(_message_envelope(message_id="wamid.plain_ya1", text="YA please confirm this one"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"


def test_invalid_confirmation_code_performs_zero_writes(monkeypatch):
    # TEST 8.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.badcode1", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    states_before = [dict(row) for row in repo.rows]

    # Well-formed (exactly 32 hex) but non-existent -- distinct from a
    # malformed/wrong-length code, which never matches at all and falls
    # through to plain-YA semantics instead (see the strict-length tests).
    response = _post(_message_envelope(message_id="wamid.badcode_ya1", text="YA WA-CONF-00000000000000000000000000000000"))

    assert response.status_code == 200
    assert [row["state"] for row in repo.rows] == [row["state"] for row in states_before]
    assert repo.rows[0].get("confirmed_by") is None
    assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")


def test_repeated_resend_of_same_intent_does_not_create_multiple_actionable_confirmations(monkeypatch):
    # TEST 4 -- reproduces the real defect's second symptom: the same
    # logical CMON request, resent as genuinely distinct WhatsApp
    # messages (distinct provider_message_id each -- e.g. an impatient
    # user retrying), must not accumulate multiple simultaneous
    # actionable confirmations. Before the fix, each resend created its
    # own pending row since delivery-key dedup only catches a literal
    # redelivery of the SAME provider_message_id, never a second,
    # independent message with equivalent content.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    text = "CMON 211-P-13AR: ditemukan kebocoran mechanical seal"
    for i in range(4):
        _post(_message_envelope(message_id=f"wamid.resend{i}", text=text))

    assert len(repo.rows) == 4  # each real message is still recorded...
    actionable = [row for row in repo.rows if row["state"] in {"NEEDS_INFORMATION", "READY_FOR_CONFIRMATION"}]
    expired = [row for row in repo.rows if row["state"] == "EXPIRED"]
    assert len(actionable) == 1  # ...but only the newest stays actionable
    assert len(expired) == 3
    assert actionable[0]["intake_id"] == repo.rows[-1]["intake_id"]

    # A plain "YA" is now unambiguous -- exactly the real user's next step.
    response = _post(_message_envelope(message_id="wamid.resend_ya1", text="YA"))
    assert response.status_code == 200
    assert repo.rows[-1]["state"] == "CONFIRMED"


def test_repeated_resend_never_expires_an_already_confirmed_row(monkeypatch):
    # A CONFIRMED reading for an asset must never be touched by a later,
    # unrelated new message for the same asset -- only still-open
    # (NEEDS_INFORMATION/READY_FOR_CONFIRMATION) rows are ever superseded.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.conf1", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    _post(_message_envelope(message_id="wamid.conf_ya1", text="YA"))
    assert repo.rows[0]["state"] == "CONFIRMED"

    _post(_message_envelope(message_id="wamid.conf2", text="CM 211-P-13AR hari ini DE 80 NDE 82 tidak bocor"))

    assert repo.rows[0]["state"] == "CONFIRMED"  # untouched
    assert repo.rows[1]["state"] in {"NEEDS_INFORMATION", "READY_FOR_CONFIRMATION"}


# --- State-guard fix: terminal-state confirmation codes never resurrect --
#
# bf8d525 fixed code parsing and duplicate-intent pending rows, but left a
# related gap: _confirm_pending only special-cased state=="CONFIRMED" --
# a code belonging to an EXPIRED (or CANCELLED, or REJECTED) row could
# still be used to resurrect and confirm it, since
# find_pending_by_confirmation_id/find_pending_by_outbound_message_id do
# exact-match lookups with no state filter at all.


def test_expired_code_rejected_and_replacement_code_confirms_normally(monkeypatch):
    # TEST A.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    text = "CMON 211-P-13AR: ditemukan kebocoran mechanical seal"
    _post(_message_envelope(message_id="wamid.supA", text=text))
    code_a = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.supB", text=text))
    code_b = repo.rows[1]["confirmation_id"]
    assert repo.rows[0]["state"] == "EXPIRED"
    assert repo.rows[1]["state"] in {"NEEDS_INFORMATION", "READY_FOR_CONFIRMATION"}

    response = _post(_message_envelope(message_id="wamid.sup_ya_a", text=f"YA {code_a}"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "EXPIRED"  # unchanged -- never resurrected
    assert repo.rows[0].get("confirmed_by") is None  # no write
    assert repo.rows[1]["state"] != "CONFIRMED"  # B untouched by this attempt
    assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")

    response_b = _post(_message_envelope(message_id="wamid.sup_ya_b", text=f"YA {code_b}"))

    assert response_b.status_code == 200
    assert repo.rows[1]["state"] == "CONFIRMED"  # the replacement confirms normally


def test_cancelled_code_rejected_and_state_unchanged(monkeypatch):
    # TEST B.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.cancA", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.cancB", text="BATAL"))
    assert repo.rows[0]["state"] == "CANCELLED"

    response = _post(_message_envelope(message_id="wamid.canc_ya", text=f"YA {code}"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CANCELLED"
    assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")


def test_rejected_code_rejected_and_state_unchanged(monkeypatch):
    # TEST C.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    # "WO 211-P-13AR broken" previously stood in for arbitrary unsupported-
    # intent text; "WO" now correctly matches the LTSA AI query router's
    # own work-orders intent (MWO: PRODUCTION READINESS + WHATSAPP -> LTSA
    # AI INTEGRATION AUDIT), so this test -- which is about REJECTED-code
    # terminal-state protection, not routing -- uses different text that
    # neither classifier recognizes, to keep testing exactly what it
    # always tested.
    _post(_message_envelope(message_id="wamid.rejA", text="Zzz 211-P-13AR unclassified nonsense message"))
    assert repo.rows[0]["state"] == "REJECTED"
    assert repo.rows[0]["detected_domain"] == "UNSUPPORTED_INTENT"
    code = repo.rows[0]["confirmation_id"]

    response = _post(_message_envelope(message_id="wamid.rej_ya", text=f"YA {code}"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "REJECTED"
    assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")


def test_confirmed_code_repeat_via_explicit_selector_does_not_re_transition(monkeypatch):
    # TEST D.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.confdA", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.confd_ya1", text="YA"))
    assert repo.rows[0]["state"] == "CONFIRMED"
    confirmed_by_first = repo.rows[0].get("confirmed_by")

    response = _post(_message_envelope(message_id="wamid.confd_ya2", text=f"YA {code}"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert repo.rows[0].get("confirmed_by") == confirmed_by_first  # no second transition
    assert outbound.calls[-1] == (SENDER_A, "Data sudah dikonfirmasi.")


def test_copied_expired_code_with_trailing_label_rejected(monkeypatch):
    # TEST E.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    text = "CMON 211-P-13AR: ditemukan kebocoran mechanical seal"
    _post(_message_envelope(message_id="wamid.cpexpA", text=text))
    code_a = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.cpexpB", text=text))
    assert repo.rows[0]["state"] == "EXPIRED"

    response = _post(
        _message_envelope(message_id="wamid.cpexp_ya", text=f"Ya {code_a}: CONDITION_MONITORING 211-P-13AR")
    )

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "EXPIRED"
    assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")


def test_four_resends_leave_one_actionable_and_no_expired_code_is_resurrectable(monkeypatch):
    # Explicit end-to-end scenario: 4 repeated/resent CMON intents -> 1
    # actionable confirmation, older rows EXPIRED, and NONE of those
    # expired codes can be resurrected via explicit selector.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    text = "CMON 211-P-13AR: ditemukan kebocoran mechanical seal"
    for i in range(4):
        _post(_message_envelope(message_id=f"wamid.foursend{i}", text=text))

    expired_codes = [row["confirmation_id"] for row in repo.rows if row["state"] == "EXPIRED"]
    assert len(expired_codes) == 3

    for code in expired_codes:
        response = _post(_message_envelope(message_id=f"wamid.foursend_ya_{code}", text=f"YA {code}"))
        assert response.status_code == 200
        assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")

    states = [row["state"] for row in repo.rows]
    assert states.count("EXPIRED") == 3
    assert states.count("CONFIRMED") == 0  # none resurrected by the attempts above


# --- Production regression fix: CONFIRMED rows must never participate in --
# --- plain-YA candidate discovery -------------------------------------------
#
# Real production E2E: same sender had 2 CONFIRMED rows + 1 NEEDS_INFORMATION
# row, all CONDITION_MONITORING/211-P-13AR. A plain "Ya" (answering AI5R's
# own missing-reading_date question) incorrectly returned
# AMBIGUOUS_PENDING_SELECTION because find_actionable_pending_list's state
# filter included CONFIRMED alongside the genuinely open states.


def test_production_regression_ya_selects_open_row_ignoring_confirmed_rows(monkeypatch):
    # TASK 3 -- mandatory exact reproduction of the real production DB state.
    from datetime import datetime, timedelta, timezone

    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)

    # Row A: a genuine prior CMON reading, confirmed.
    _post(_message_envelope(message_id="wamid.prodA1", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    _post(_message_envelope(message_id="wamid.prodA2", text="YA"))
    assert repo.rows[0]["state"] == "CONFIRMED"

    # Row B: a second, later genuine reading for the same asset, also confirmed.
    _post(_message_envelope(message_id="wamid.prodB1", text="CM 211-P-13AR hari ini DE 80 NDE 82 tidak bocor"))
    _post(_message_envelope(message_id="wamid.prodB2", text="YA"))
    assert repo.rows[1]["state"] == "CONFIRMED"

    # Row C: the real production message, missing reading_date.
    _post(_message_envelope(message_id="wamid.prodC1", text="CMON 211-P-13AR: ditemukan kebocoran mechanical seal"))
    assert repo.rows[2]["state"] == "NEEDS_INFORMATION"
    assert len(repo.rows) == 3

    expected_today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()

    response = _post(_message_envelope(message_id="wamid.prodC2", text="Ya"))

    assert response.status_code == 200
    reply_text = outbound.calls[-1][1]
    assert "Ada beberapa data menunggu konfirmasi" not in reply_text  # NOT ambiguous
    assert repo.rows[2]["structured_payload"]["reading_date"] == expected_today
    assert repo.rows[2]["state"] == "CONFIRMED"  # C proceeds -- date was its only gap
    assert repo.rows[0]["state"] == "CONFIRMED"  # A untouched
    assert repo.rows[1]["state"] == "CONFIRMED"  # B untouched
    assert len(repo.rows) == 3  # no new duplicate pending row


def test_one_open_row_among_ten_confirmed_is_still_selected_unambiguously(monkeypatch):
    # TASK 4 Test A.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    for i in range(10):
        tag = "211-P-13AR" if i % 2 == 0 else "210-P-05AR"
        _post(_message_envelope(message_id=f"wamid.tenA{i}", text=f"CM {tag} hari ini DE 7{i} NDE 8{i} tidak bocor"))
        _post(_message_envelope(message_id=f"wamid.tenAya{i}", text="YA"))
    assert sum(1 for r in repo.rows if r["state"] == "CONFIRMED") == 10

    _post(_message_envelope(message_id="wamid.tenA_open", text="CMON 211-P-13AR: ditemukan kebocoran mechanical seal"))
    open_row_id = repo.rows[-1]["intake_id"]
    assert repo.rows[-1]["state"] == "NEEDS_INFORMATION"

    response = _post(_message_envelope(message_id="wamid.tenA_ya", text="YA"))

    assert response.status_code == 200
    updated = [r for r in repo.rows if r["intake_id"] == open_row_id][0]
    assert updated["state"] == "CONFIRMED"
    assert sum(1 for r in repo.rows if r["state"] == "CONFIRMED") == 11


def test_ready_for_confirmation_row_among_confirmed_rows_is_still_selected(monkeypatch):
    # TASK 4 Test B.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    for i in range(3):
        tag = "211-P-13AR" if i % 2 == 0 else "210-P-05AR"
        _post(_message_envelope(message_id=f"wamid.readyconf{i}", text=f"CM {tag} hari ini DE 7{i} NDE 8{i} tidak bocor"))
        _post(_message_envelope(message_id=f"wamid.readyconf_ya{i}", text="YA"))
    assert sum(1 for r in repo.rows if r["state"] == "CONFIRMED") == 3

    _post(_message_envelope(message_id="wamid.ready_open", text="CM 210-P-05AR hari ini DE 90 NDE 91 tidak bocor"))
    ready_row_id = repo.rows[-1]["intake_id"]
    assert repo.rows[-1]["state"] == "READY_FOR_CONFIRMATION"

    response = _post(_message_envelope(message_id="wamid.ready_ya", text="YA"))

    assert response.status_code == 200
    updated = [r for r in repo.rows if r["intake_id"] == ready_row_id][0]
    assert updated["state"] == "CONFIRMED"


def test_only_confirmed_rows_plain_ya_is_not_ambiguous_uses_no_pending_reply(monkeypatch):
    # TASK 4 Test C -- must use the existing correct no-pending response,
    # never the "Ada beberapa data menunggu konfirmasi" ambiguity reply.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)
    _post(_message_envelope(message_id="wamid.onlyconfA", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    _post(_message_envelope(message_id="wamid.onlyconfA_ya", text="YA"))
    assert repo.rows[0]["state"] == "CONFIRMED"

    response = _post(_message_envelope(message_id="wamid.onlyconf_ya2", text="YA"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Tidak ada data yang menunggu konfirmasi.")


# --- Authoritative WhatsApp CMON writer -------------------------------------

_PRODUCTION_CMON_TEXT = "CMON 211-P-13AR: ditemukan kebocoran mechanical seal"


def test_cmon_write_exact_production_flow_creates_one_canonical_record(monkeypatch):
    # CMON_WRITE_TEST -- the mandatory exact production reproduction.
    from datetime import datetime, timedelta, timezone

    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.cmonwriteA", text=_PRODUCTION_CMON_TEXT))
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"
    assert outbound.calls[-1] == (SENDER_A, "Reading date belum ada. Gunakan hari ini?")

    # First "Ya" answers the missing-date question only -- it must NOT
    # write anything yet, only move the row to READY_FOR_CONFIRMATION and
    # show the preview.
    mid_response = _post(_message_envelope(message_id="wamid.cmonwriteB", text="Ya"))
    assert mid_response.status_code == 200
    assert cmon.rows == []
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    assert outbound.calls[-1][1].endswith("Confirm?\nYA / UBAH / BATAL")

    # Second, separate "Ya" is the real final confirmation.
    response = _post(_message_envelope(message_id="wamid.cmonwriteC", text="Ya"))

    assert response.status_code == 200
    assert len(cmon.rows) == 1
    assert repo.rows[0]["state"] == "CONFIRMED"
    expected_today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    reply = outbound.calls[-1][1]
    assert "berhasil disimpan" in reply
    assert "Terkonfirmasi sebagai draft intake" not in reply
    assert cmon.rows[0]["reading_date"] == expected_today


def test_cmon_golden_flow_matches_pm_interaction_parity(monkeypatch):
    # MWO: PRODUCTION READINESS + WHATSAPP -> LTSA AI INTEGRATION AUDIT,
    # Phase 3 -- proves CMON confirmation already follows the exact same
    # interaction shape as PM's own golden flow (test_pm_write_exact_flow_
    # creates_one_canonical_record): missing-field question, preview,
    # canonical write with a truthful success message, then a fourth "Ya"
    # correctly reports nothing pending -- the full 4-message conversation
    # in one place, not scattered across separate tests. No code change
    # was needed here; this documents/guards the already-correct behavior.
    from datetime import datetime, timedelta, timezone
    expected_today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()

    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.cmonparityA", text=_PRODUCTION_CMON_TEXT))
    assert outbound.calls[-1] == (SENDER_A, "Reading date belum ada. Gunakan hari ini?")

    _post(_message_envelope(message_id="wamid.cmonparityB", text="YA"))
    assert outbound.calls[-1] == (
        SENDER_A,
        f"Condition Monitoring\nPump: 211-P-13AR\nDate: {expected_today}\nLeak: Yes\n\nConfirm?\nYA / UBAH / BATAL",
    )
    assert cmon.rows == []

    _post(_message_envelope(message_id="wamid.cmonparityC", text="YA"))
    canonical_code = cmon.rows[0]["condition_monitoring_reading_code"]
    assert outbound.calls[-1] == (
        SENDER_A,
        f"Condition Monitoring 211-P-13AR berhasil disimpan.\nTanggal: {expected_today}\nKode: {canonical_code}",
    )
    assert len(cmon.rows) == 1

    # Repeated "YA" -- no duplicate write, pending state correctly cleared.
    _post(_message_envelope(message_id="wamid.cmonparityD", text="YA"))
    assert outbound.calls[-1] == (SENDER_A, "Tidak ada data yang menunggu konfirmasi.")
    assert len(cmon.rows) == 1


def test_cmon_field_mapping_matches_structured_payload(monkeypatch):
    # CMON_FIELD_MAPPING_TEST.
    from datetime import datetime, timedelta, timezone

    repo = FakeIntakeRepository({SENDER_A: _identity(user_id="user-mapping-1")})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.mapA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.mapB", text="Ya"))  # answers missing-date question only
    _post(_message_envelope(message_id="wamid.mapC", text="Ya"))  # final confirmation -- writes

    record = cmon.rows[0]
    expected_today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    assert record["asset_code"] == "211-P-13AR"
    assert record["asset_type"] == "PUMP"
    assert record["reading_date"] == expected_today
    assert record["finding"] == "ditemukan kebocoran mechanical seal"
    assert record["created_by"] == "user-mapping-1"
    assert record["provenance"] == "WHATSAPP"
    assert record["source_reference"] == f"WHATSAPP::{repo.rows[0]['intake_id']}"
    # Never fabricated -- no vibration/temperature/pressure/severity value
    # was ever supplied by this message, so none is invented here.
    assert record["measurements"].get("mechseal_temp_de") is None
    assert record["measurements"].get("vertical_vibration_de") is None


def test_cmon_zero_open_schedules_uses_unscheduled_sentinel(monkeypatch):
    # ZERO_SCHEDULE_ADHOC_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository(schedules=[])
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.zeroschedA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.zeroschedB", text="Ya"))
    _post(_message_envelope(message_id="wamid.zeroschedC", text="Ya"))

    assert len(cmon.rows) == 1
    assert cmon.rows[0]["condition_monitoring_schedule_code"] == "UNSCHEDULED::WHATSAPP"
    assert cmon.create_ad_hoc_draft_calls == [f"WHATSAPP::{repo.rows[0]['intake_id']}"]
    assert cmon.create_draft_calls == []


def test_cmon_one_open_schedule_uses_real_schedule_code(monkeypatch):
    # ONE_SCHEDULE_RESOLUTION_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository(
        schedules=[{"condition_monitoring_schedule_code": "CMSCHED-REAL-1", "asset_code": "211-P-13AR", "status": "ACTIVE", "frequency": "Weekly"}]
    )
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.oneschedA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.oneschedB", text="Ya"))
    _post(_message_envelope(message_id="wamid.oneschedC", text="Ya"))

    assert len(cmon.rows) == 1
    assert cmon.rows[0]["condition_monitoring_schedule_code"] == "CMSCHED-REAL-1"
    assert not cmon.rows[0]["condition_monitoring_schedule_code"].startswith("UNSCHEDULED")
    assert cmon.create_draft_calls == ["CMSCHED-REAL-1"]
    assert cmon.create_ad_hoc_draft_calls == []


def test_cmon_multiple_open_schedules_returns_clarification_no_write(monkeypatch):
    # MULTIPLE_SCHEDULE_CLARIFICATION_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository(
        schedules=[
            {"condition_monitoring_schedule_code": "CMSCHED-A", "asset_code": "211-P-13AR", "status": "ACTIVE", "frequency": "Weekly"},
            {"condition_monitoring_schedule_code": "CMSCHED-B", "asset_code": "211-P-13AR", "status": "PLANNED", "frequency": "Monthly"},
        ]
    )
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.multischedA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.multischedB", text="Ya"))  # answers missing-date question only
    response = _post(_message_envelope(message_id="wamid.multischedC", text="Ya"))  # final confirmation -- hits ambiguity

    assert response.status_code == 200
    assert cmon.rows == []  # no write at all
    assert repo.rows[0]["state"] != "CONFIRMED"  # pending stays unresolved
    reply = outbound.calls[-1][1]
    assert "Ditemukan lebih dari satu jadwal" in reply
    assert "Weekly" in reply and "Monthly" in reply
    # Never a raw internal schedule code exposed as the only identifier.
    assert "CMSCHED-A" not in reply
    assert "CMSCHED-B" not in reply


def test_cmon_only_terminal_schedules_treated_as_zero_open(monkeypatch):
    # TERMINAL_SCHEDULE_ADHOC_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository(
        schedules=[
            {"condition_monitoring_schedule_code": "CMSCHED-DONE", "asset_code": "211-P-13AR", "status": "COMPLETED", "frequency": "Weekly"},
            {"condition_monitoring_schedule_code": "CMSCHED-CANCEL", "asset_code": "211-P-13AR", "status": "CANCELLED", "frequency": "Weekly"},
        ]
    )
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.termschedA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.termschedB", text="Ya"))
    _post(_message_envelope(message_id="wamid.termschedC", text="Ya"))

    assert len(cmon.rows) == 1
    assert cmon.rows[0]["condition_monitoring_schedule_code"] == "UNSCHEDULED::WHATSAPP"


def test_cmon_repeated_confirmation_does_not_duplicate_canonical_record(monkeypatch):
    # CMON_REPEATED_CONFIRMATION_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.repconfA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.repconfB", text="Ya"))  # answers missing-date question only
    _post(_message_envelope(message_id="wamid.repconfC", text="Ya"))  # final confirmation -- writes
    assert len(cmon.rows) == 1

    response = _post(_message_envelope(message_id="wamid.repconfD", text="YA"))

    assert response.status_code == 200
    assert len(cmon.rows) == 1  # no second canonical record


def test_cmon_duplicate_webhook_delivery_does_not_duplicate_canonical_record(monkeypatch):
    # CMON_DUPLICATE_WEBHOOK_TEST -- redelivery of the SAME "Ya" event.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.dupwebA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.dupwebB", text="Ya"))  # answers missing-date question only
    body = json.dumps(_message_envelope(message_id="wamid.dupwebC", text="Ya")).encode("utf-8")
    signature = {"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    first = client.post(WEBHOOK_PATH, content=body, headers=signature)
    second = client.post(WEBHOOK_PATH, content=body, headers=signature)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(cmon.rows) == 1


def test_cmon_explicit_code_repeat_does_not_duplicate_canonical_record(monkeypatch):
    # CMON_EXPLICIT_REPEAT_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.explrepA", text=_PRODUCTION_CMON_TEXT))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.explrepB", text="Ya"))  # answers missing-date question only
    _post(_message_envelope(message_id="wamid.explrepC", text="Ya"))  # final confirmation -- writes
    assert len(cmon.rows) == 1

    response = _post(_message_envelope(message_id="wamid.explrepD", text=f"YA {code}"))

    assert response.status_code == 200
    assert len(cmon.rows) == 1
    assert outbound.calls[-1] == (SENDER_A, f"Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: {cmon.rows[0]['condition_monitoring_reading_code']}")


def test_cmon_idempotent_recovery_when_write_succeeded_but_intake_transition_did_not(monkeypatch):
    # Durable idempotency proof for the exact gap true cross-repository
    # atomicity can't close (see TRANSACTION_BOUNDARY in the final
    # report): a prior attempt's canonical write succeeded but the
    # process never reached transition_pending (crash/network failure in
    # between). Retrying must find the existing row by source_reference
    # and complete the intake transition -- never write a second record.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.recoverA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.recoverB", text="Ya"))  # answers missing-date question only
    intake_id = repo.rows[0]["intake_id"]
    # Simulate the CMON write having already succeeded on a prior final-
    # confirmation attempt that crashed before the intake's own CONFIRMED
    # transition. Only reachable from READY_FOR_CONFIRMATION now -- a real
    # write attempt can no longer originate from NEEDS_INFORMATION.
    cmon.rows.append(
        {
            "condition_monitoring_reading_code": "CMONR-PRIOR0001",
            "condition_monitoring_schedule_code": "UNSCHEDULED::WHATSAPP",
            "asset_code": "211-P-13AR",
            "reading_date": "2026-08-29",
            "source_reference": f"WHATSAPP::{intake_id}",
        }
    )
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"  # never completed last time

    response = _post(_message_envelope(message_id="wamid.recoverC", text="Ya"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert len(cmon.rows) == 1  # still exactly the one pre-existing record
    assert outbound.calls[-1][1] != "Gagal menyimpan Condition Monitoring. Silakan coba lagi."


def test_cmon_write_failure_does_not_confirm_or_send_false_success(monkeypatch):
    # CMON_WRITE_FAILURE_ROLLBACK_TEST + NO_FALSE_SUCCESS_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository(fail=True)
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.failA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.failB", text="Ya"))  # answers missing-date question only
    response = _post(_message_envelope(message_id="wamid.failC", text="Ya"))  # final confirmation -- attempts write

    assert response.status_code == 200
    assert cmon.rows == []
    assert repo.rows[0]["state"] != "CONFIRMED"
    reply = outbound.calls[-1][1]
    assert "berhasil" not in reply
    assert "Berhasil" not in reply
    assert reply == "Gagal menyimpan Condition Monitoring. Silakan coba lagi."


def test_cmon_wrong_sender_never_reaches_canonical_write(monkeypatch):
    # CMON_WRONG_SENDER_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id="user-a"), SENDER_B: _identity(user_id="user-b")})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.wrongsenderA", sender="15550000001", text=_PRODUCTION_CMON_TEXT))
    response = _post(_message_envelope(message_id="wamid.wrongsenderB", sender="15550000002", text="Ya"))

    assert response.status_code == 200
    assert cmon.rows == []
    assert cmon.create_draft_calls == []
    assert cmon.create_ad_hoc_draft_calls == []
    assert repo.rows[0]["state"] != "CONFIRMED"


def test_cmon_wrong_org_never_reaches_canonical_write(monkeypatch):
    # CMON_WRONG_ORG_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity(organization_id="org-tap")})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.wrongorgA", text=_PRODUCTION_CMON_TEXT))
    repo.rows[0]["organization_id"] = "org-other"  # simulate a stored row from a different org

    response = _post(_message_envelope(message_id="wamid.wrongorgB", text="Ya"))

    assert response.status_code == 200
    assert cmon.rows == []
    assert repo.rows[0]["state"] != "CONFIRMED"


def test_cmon_unknown_asset_never_reaches_canonical_write(monkeypatch):
    # CMON_UNKNOWN_ASSET_TEST -- existing UNKNOWN_PUMP validation already
    # blocks confirmation before the CMON-write step is ever reached.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.unkassetA", text="CM 999-P-99 hari ini DE 78 NDE 81 tidak bocor"))
    assert "UNKNOWN_PUMP" in repo.rows[0]["validation_result"]["errors"]

    response = _post(_message_envelope(message_id="wamid.unkassetB", text="Ya"))

    assert response.status_code == 200
    assert cmon.rows == []
    assert repo.rows[0]["state"] != "CONFIRMED"


# --- Authoritative WhatsApp PM writer (MWO: AUTHORITATIVE WHATSAPP PM
# CANONICAL PERSISTENCE) -- mirrors the CMON writer test suite's shape
# above, adapted to PM's own schema/semantics (51667f9's repository
# support), never copying CMON assumptions blindly.

_PRODUCTION_PM_TEXT = "PM 211-P-13AR ganti oli mesin"


def test_pm_write_exact_flow_creates_one_canonical_record(monkeypatch):
    # PM_WRITE_TEST -- missing occurrence_date, resolved via the SAME
    # two-step state-machine boundary fee571a already established: the
    # first "Ya" answers the date question only (zero canonical writes),
    # a genuinely separate second "Ya" performs the final write.
    from datetime import datetime, timedelta, timezone

    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmwriteA", text=_PRODUCTION_PM_TEXT))
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"
    assert outbound.calls[-1] == (SENDER_A, "Tanggal PM belum ada. Gunakan hari ini?")

    mid_response = _post(_message_envelope(message_id="wamid.pmwriteB", text="Ya"))
    assert mid_response.status_code == 200
    assert pm.rows == []
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    assert outbound.calls[-1][1].endswith("Confirm?\nYA / UBAH / BATAL")

    response = _post(_message_envelope(message_id="wamid.pmwriteC", text="Ya"))

    assert response.status_code == 200
    assert len(pm.rows) == 1
    assert repo.rows[0]["state"] == "CONFIRMED"
    expected_today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    reply = outbound.calls[-1][1]
    assert "berhasil disimpan" in reply
    assert "Terkonfirmasi sebagai draft intake" not in reply
    assert pm.rows[0]["occurrence_date"] == expected_today


def test_pm_field_mapping_matches_structured_payload(monkeypatch):
    # PM_FIELD_MAPPING_TEST.
    from datetime import datetime, timedelta, timezone

    repo = FakeIntakeRepository({SENDER_A: _identity(user_id="user-mapping-pm-1")})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmmapA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmmapB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmmapC", text="Ya"))

    record = pm.rows[0]
    expected_today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    assert record["asset_code"] == "211-P-13AR"
    assert record["asset_type"] == "PUMP"
    assert record["occurrence_date"] == expected_today
    assert record["activities"] == [{"code": "WHATSAPP-FREE-TEXT", "description": "ganti oli mesin", "side": None, "done": False}]
    assert record["created_by"] == "user-mapping-pm-1"
    assert record["provenance"] == "WHATSAPP"
    assert record["source_reference"] == f"WHATSAPP::{repo.rows[0]['intake_id']}"
    # Never invented -- remarks was never supplied by this message.
    assert record.get("remarks") is None


def test_pm_leading_colon_after_tag_stripped_from_activity_description(monkeypatch):
    # Cosmetic fix -- "PM <tag>: <activity>" previously left a leading ":"
    # attached to the activity description (rendered as the doubled
    # "Activity: : check strainer" in the preview). Brings PM in line
    # with _extract_cmon_finding's own identical leading-colon strip for
    # the same "CMON <tag>: <finding>" shape.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    # Exact golden-flow shape: "PM <tag>: <activity>", no date -- the
    # colon lands immediately after the tag, which is exactly the case
    # that previously leaked through as a leading ":".
    _post(_message_envelope(message_id="wamid.pmcolonA", text="PM 211-P-13AR: check strainer"))
    activities = repo.rows[0]["structured_payload"]["activities"]
    assert activities == [{"code": "WHATSAPP-FREE-TEXT", "description": "check strainer", "side": None, "done": False}]

    # "Ya" resolves the date, producing the preview that used to show the
    # doubled "Activity: : check strainer".
    _post(_message_envelope(message_id="wamid.pmcolonB", text="Ya"))
    reply = outbound.calls[-1][1]
    assert "Activity: check strainer" in reply
    assert "Activity: : " not in reply


def test_pm_zero_open_schedules_uses_unscheduled_sentinel(monkeypatch):
    # PM_ZERO_SCHEDULE_ADHOC_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository(schedules=[])
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmzeroschedA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmzeroschedB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmzeroschedC", text="Ya"))

    assert len(pm.rows) == 1
    assert pm.rows[0]["pm_schedule_code"] == "UNSCHEDULED::WHATSAPP"
    assert pm.create_ad_hoc_draft_calls == [f"WHATSAPP::{repo.rows[0]['intake_id']}"]
    assert pm.create_draft_calls == []


def test_pm_one_open_schedule_uses_real_schedule_code(monkeypatch):
    # PM_ONE_SCHEDULE_RESOLUTION_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository(
        schedules=[{"pm_schedule_code": "PMSCHED-REAL-1", "asset_code": "211-P-13AR", "status": "ACTIVE", "procedure": "Lubrication"}]
    )
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmoneschedA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmoneschedB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmoneschedC", text="Ya"))

    assert len(pm.rows) == 1
    assert pm.rows[0]["pm_schedule_code"] == "PMSCHED-REAL-1"
    assert not pm.rows[0]["pm_schedule_code"].startswith("UNSCHEDULED")
    assert pm.create_draft_calls == ["PMSCHED-REAL-1"]
    assert pm.create_ad_hoc_draft_calls == []


def test_pm_multiple_open_schedules_returns_clarification_no_write(monkeypatch):
    # PM_MULTIPLE_SCHEDULE_CLARIFICATION_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository(
        schedules=[
            {"pm_schedule_code": "PMSCHED-A", "asset_code": "211-P-13AR", "status": "ACTIVE", "procedure": "Lubrication"},
            {"pm_schedule_code": "PMSCHED-B", "asset_code": "211-P-13AR", "status": "PLANNED", "procedure": "Inspection"},
        ]
    )
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmmultischedA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmmultischedB", text="Ya"))  # answers date question only
    response = _post(_message_envelope(message_id="wamid.pmmultischedC", text="Ya"))  # final confirmation -- hits ambiguity

    assert response.status_code == 200
    assert pm.rows == []  # no write at all
    assert repo.rows[0]["state"] != "CONFIRMED"  # pending stays unresolved
    reply = outbound.calls[-1][1]
    assert "Ditemukan lebih dari satu jadwal PM" in reply
    assert "Lubrication" in reply and "Inspection" in reply
    # Never a raw internal schedule code exposed as the only identifier.
    assert "PMSCHED-A" not in reply
    assert "PMSCHED-B" not in reply


def test_pm_only_terminal_schedules_treated_as_zero_open(monkeypatch):
    # PM_TERMINAL_SCHEDULE_ADHOC_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository(
        schedules=[
            {"pm_schedule_code": "PMSCHED-DONE", "asset_code": "211-P-13AR", "status": "COMPLETED", "procedure": "Lubrication"},
            {"pm_schedule_code": "PMSCHED-CANCEL", "asset_code": "211-P-13AR", "status": "CANCELLED", "procedure": "Inspection"},
        ]
    )
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmtermschedA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmtermschedB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmtermschedC", text="Ya"))

    assert len(pm.rows) == 1
    assert pm.rows[0]["pm_schedule_code"] == "UNSCHEDULED::WHATSAPP"


def test_pm_repeated_confirmation_does_not_duplicate_canonical_record(monkeypatch):
    # PM_REPEATED_CONFIRMATION_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmrepconfA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmrepconfB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmrepconfC", text="Ya"))
    assert len(pm.rows) == 1

    response = _post(_message_envelope(message_id="wamid.pmrepconfD", text="YA"))

    assert response.status_code == 200
    assert len(pm.rows) == 1  # no second canonical record


def test_pm_duplicate_webhook_delivery_does_not_duplicate_canonical_record(monkeypatch):
    # PM_DUPLICATE_WEBHOOK_TEST -- redelivery of the SAME final "Ya" event.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmdupwebA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmdupwebB", text="Ya"))  # answers date question only
    body = json.dumps(_message_envelope(message_id="wamid.pmdupwebC", text="Ya")).encode("utf-8")
    signature = {"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    first = client.post(WEBHOOK_PATH, content=body, headers=signature)
    second = client.post(WEBHOOK_PATH, content=body, headers=signature)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(pm.rows) == 1


def test_pm_explicit_code_repeat_does_not_duplicate_canonical_record(monkeypatch):
    # PM_EXPLICIT_REPEAT_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmexplrepA", text=_PRODUCTION_PM_TEXT))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.pmexplrepB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmexplrepC", text="Ya"))
    assert len(pm.rows) == 1

    response = _post(_message_envelope(message_id="wamid.pmexplrepD", text=f"YA {code}"))

    assert response.status_code == 200
    assert len(pm.rows) == 1
    assert outbound.calls[-1] == (SENDER_A, f"PM 211-P-13AR sudah tersimpan sebelumnya.\nKode: {pm.rows[0]['pm_occurrence_code']}")


def test_pm_idempotent_recovery_when_write_succeeded_but_intake_transition_did_not(monkeypatch):
    # Durable idempotency proof for the exact gap true cross-repository
    # atomicity can't close: a prior attempt's canonical write succeeded
    # but the process never reached transition_pending. Retrying must
    # find the existing row by source_reference and complete the intake
    # transition -- never write a second record.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmrecoverA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmrecoverB", text="Ya"))  # answers date question only
    intake_id = repo.rows[0]["intake_id"]
    # Simulate the CMON... err, PM write having already succeeded on a
    # prior final-confirmation attempt that crashed before the intake's
    # own CONFIRMED transition. Only reachable from READY_FOR_CONFIRMATION.
    pm.rows.append(
        {
            "pm_occurrence_code": "PMOCC-PRIOR0001",
            "pm_schedule_code": "UNSCHEDULED::WHATSAPP",
            "asset_code": "211-P-13AR",
            "occurrence_date": "2026-08-30",
            "source_reference": f"WHATSAPP::{intake_id}",
        }
    )
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"  # never completed last time

    response = _post(_message_envelope(message_id="wamid.pmrecoverC", text="Ya"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert len(pm.rows) == 1  # still exactly the one pre-existing record
    assert outbound.calls[-1][1] != "Gagal menyimpan PM. Silakan coba lagi."


def test_pm_write_failure_does_not_confirm_or_send_false_success(monkeypatch):
    # PM_WRITE_FAILURE_ROLLBACK_TEST + NO_FALSE_SUCCESS_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository(fail=True)
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmfailA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmfailB", text="Ya"))  # answers date question only
    response = _post(_message_envelope(message_id="wamid.pmfailC", text="Ya"))  # final confirmation -- attempts write

    assert response.status_code == 200
    assert pm.rows == []
    assert repo.rows[0]["state"] != "CONFIRMED"
    reply = outbound.calls[-1][1]
    assert "berhasil" not in reply
    assert "Berhasil" not in reply
    assert reply == "Gagal menyimpan PM. Silakan coba lagi."


def test_pm_wrong_sender_never_reaches_canonical_write(monkeypatch):
    # PM_WRONG_SENDER_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id="user-a"), SENDER_B: _identity(user_id="user-b")})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmwrongsenderA", sender="15550000001", text=_PRODUCTION_PM_TEXT))
    response = _post(_message_envelope(message_id="wamid.pmwrongsenderB", sender="15550000002", text="Ya"))

    assert response.status_code == 200
    assert pm.rows == []
    assert pm.create_draft_calls == []
    assert pm.create_ad_hoc_draft_calls == []
    assert repo.rows[0]["state"] != "CONFIRMED"


def test_pm_wrong_org_never_reaches_canonical_write(monkeypatch):
    # PM_WRONG_ORG_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity(organization_id="org-tap")})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmwrongorgA", text=_PRODUCTION_PM_TEXT))
    repo.rows[0]["organization_id"] = "org-other"  # simulate a stored row from a different org

    response = _post(_message_envelope(message_id="wamid.pmwrongorgB", text="Ya"))

    assert response.status_code == 200
    assert pm.rows == []
    assert repo.rows[0]["state"] != "CONFIRMED"


def test_pm_unknown_asset_never_reaches_canonical_write(monkeypatch):
    # PM_UNKNOWN_ASSET_TEST -- existing UNKNOWN_PUMP validation already
    # blocks confirmation before the PM-write step is ever reached.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmunkassetA", text="PM 999-P-99 ganti oli"))
    assert "UNKNOWN_PUMP" in repo.rows[0]["validation_result"]["errors"]

    response = _post(_message_envelope(message_id="wamid.pmunkassetB", text="Ya"))

    assert response.status_code == 200
    assert pm.rows == []
    assert repo.rows[0]["state"] != "CONFIRMED"


def test_confirmed_pm_explicit_retry_returns_existing_canonical_code(monkeypatch):
    # Mirrors the CMON confirmed-retry disclosure test exactly, for PM.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmconfretryA", text=_PRODUCTION_PM_TEXT))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.pmconfretryB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmconfretryC", text="Ya"))
    assert repo.rows[0]["state"] == "CONFIRMED"
    canonical_code = pm.rows[0]["pm_occurrence_code"]
    confirmed_by_before = repo.rows[0].get("confirmed_by")
    create_draft_calls_before = list(pm.create_draft_calls)
    create_ad_hoc_draft_calls_before = list(pm.create_ad_hoc_draft_calls)

    response = _post(_message_envelope(message_id="wamid.pmconfretryD", text=f"YA {code}"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, f"PM 211-P-13AR sudah tersimpan sebelumnya.\nKode: {canonical_code}")
    assert len(pm.rows) == 1
    assert pm.create_draft_calls == create_draft_calls_before
    assert pm.create_ad_hoc_draft_calls == create_ad_hoc_draft_calls_before
    assert repo.rows[0].get("confirmed_by") == confirmed_by_before
    assert repo.rows[0]["state"] == "CONFIRMED"


def test_confirmed_pm_lowercase_explicit_code_works(monkeypatch):
    # Confirmation-security regression: PM must benefit from the same
    # case-insensitive-prefix/strict-32-hex confirmation code fix as CMON
    # (f76fcbb), since both go through the exact same _handle_existing_
    # pending_action/_CONFIRMATION_CODE_PATTERN code path.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmlowerA", text=_PRODUCTION_PM_TEXT))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.pmlowerB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmlowerC", text="Ya"))
    canonical_code = pm.rows[0]["pm_occurrence_code"]

    response = _post(_message_envelope(message_id="wamid.pmlowerD", text=f"YA {code.lower()}"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, f"PM 211-P-13AR sudah tersimpan sebelumnya.\nKode: {canonical_code}")
    assert len(pm.rows) == 1


@pytest.mark.parametrize("terminal_state", ["EXPIRED", "CANCELLED", "REJECTED"])
def test_pm_terminal_state_never_resurrects(monkeypatch, terminal_state):
    # PM_TERMINAL_STATE_TEST -- mirrors the CMON version exactly.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id=f"wamid.pmtermF1{terminal_state}", text=_PRODUCTION_PM_TEXT))
    code = repo.rows[0]["confirmation_id"]
    repo.rows[0]["state"] = terminal_state

    response = _post(_message_envelope(message_id=f"wamid.pmtermF2{terminal_state}", text=f"YA {code}"))

    assert response.status_code == 200
    assert pm.rows == []
    assert repo.rows[0]["state"] == terminal_state
    assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")


def test_pm_plain_ya_does_not_select_confirmed_row(monkeypatch):
    # PM_PLAIN_YA_SELECTION_TEST -- mirrors the CMON version exactly.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.pmplainyaA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmplainyaB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmplainyaC", text="Ya"))
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert len(pm.rows) == 1

    response = _post(_message_envelope(message_id="wamid.pmplainyaD", text="Ya"))

    assert response.status_code == 200
    assert len(pm.rows) == 1
    assert outbound.calls[-1] == (SENDER_A, "Tidak ada data yang menunggu konfirmasi.")


# --- Phase 9: routing/UX regression -- no PM/CMON cross-routing --------

@pytest.mark.parametrize(
    "text",
    [
        "PM 211-P-13AR: ganti oli",
        "PM 211-P-13AR tanggal 29-08-2026: ganti oli",
        "PM 211-P-13AR hari ini: ganti oli",
    ],
    ids=["no_date", "unparsed_explicit_date", "hari_ini"],
)
def test_pm_message_variants_classify_as_pm_never_cmon(monkeypatch, text):
    # "tanggal 29-08-2026" is NOT currently parsed as an explicit date by
    # _extract_payload (only "hari ini"/"today" is) -- that variant
    # correctly still classifies as PM and falls through to the missing-
    # date follow-up, exactly like the no-date variant. This is an
    # existing, unmodified limitation (documented, not fixed here -- out
    # of this MWO's scope), not a routing defect: the point under test is
    # that domain classification never cross-routes to CMON regardless.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm)

    response = _post(_message_envelope(message_id=f"wamid.pmroute{hash(text)}", text=text))

    assert response.status_code == 200
    assert repo.rows[0]["detected_domain"] == "PM"


def test_cmon_message_still_routes_exclusively_to_cmon(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon, pm_repository=pm)

    _post(_message_envelope(message_id="wamid.cmonroute", text="CMON 211-P-13AR: ditemukan kebocoran mechanical seal"))

    assert repo.rows[0]["detected_domain"] == "CONDITION_MONITORING"


# --- Ordering-bug fix: state-machine boundary between "answer a missing-
# information question" and "final confirmation" -----------------------

def test_production_ordering_bug_exact_three_message_regression(monkeypatch):
    # EXACT_THREE_MESSAGE_REGRESSION -- verbatim reproduction of the
    # production conversation that exposed the bug: a plain "Ya" that
    # only answers AI5R's own "Reading date belum ada. Gunakan hari ini?"
    # question must NOT trigger the canonical write. It must take a
    # second, separate "Ya" against an already-READY_FOR_CONFIRMATION row.
    from datetime import datetime, timedelta, timezone

    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    # Message 1: original report, missing reading_date.
    _post(_message_envelope(message_id="wamid.prod3A", text=_PRODUCTION_CMON_TEXT))
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"
    assert cmon.rows == []
    assert outbound.calls[-1] == (SENDER_A, "Reading date belum ada. Gunakan hari ini?")

    # Message 2: "Ya" answers the date question ONLY. Zero canonical
    # writes must happen here -- this is exactly what production got
    # wrong. The row must move to READY_FOR_CONFIRMATION and show a
    # preview asking for the real, separate confirmation.
    second = _post(_message_envelope(message_id="wamid.prod3B", text="Ya"))
    assert second.status_code == 200
    assert cmon.rows == []
    assert cmon.create_draft_calls == []
    assert cmon.create_ad_hoc_draft_calls == []
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    assert repo.rows[0].get("confirmed_by") is None
    reply_after_second = outbound.calls[-1][1]
    assert reply_after_second.endswith("Confirm?\nYA / UBAH / BATAL")
    assert "berhasil disimpan" not in reply_after_second

    # Message 3: a genuinely separate "Ya" is the real final confirmation.
    # Only now may the canonical write happen.
    third = _post(_message_envelope(message_id="wamid.prod3C", text="Ya"))
    assert third.status_code == 200
    assert len(cmon.rows) == 1
    expected_today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    assert cmon.rows[0]["reading_date"] == expected_today
    assert cmon.rows[0]["asset_code"] == "211-P-13AR"
    assert repo.rows[0]["state"] == "CONFIRMED"
    reply_after_third = outbound.calls[-1][1]
    assert "berhasil disimpan" in reply_after_third


def test_state_matrix_needs_information_plus_ya_does_not_write(monkeypatch):
    # NEEDS_INFO_NO_WRITE_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.matrixA1", text=_PRODUCTION_CMON_TEXT))
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"

    _post(_message_envelope(message_id="wamid.matrixA2", text="Ya"))

    assert cmon.rows == []
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"


def test_state_matrix_ready_for_confirmation_plus_ya_writes(monkeypatch):
    # READY_CONFIRM_WRITE_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.matrixB1", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.matrixB2", text="Ya"))  # -> READY_FOR_CONFIRMATION
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"

    _post(_message_envelope(message_id="wamid.matrixB3", text="Ya"))

    assert len(cmon.rows) == 1
    assert repo.rows[0]["state"] == "CONFIRMED"


def test_state_matrix_needs_information_plus_explicit_code_does_not_write(monkeypatch):
    # EXPLICIT_NEEDS_INFO_TEST -- an explicit confirmation code must not
    # bypass the missing-information gate either; the fix lives inside
    # _confirm_pending, which explicit-code resolution also flows through.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.matrixC1", text=_PRODUCTION_CMON_TEXT))
    code = repo.rows[0]["confirmation_id"]
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"

    _post(_message_envelope(message_id="wamid.matrixC2", text=f"YA {code}"))

    assert cmon.rows == []
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"


def test_state_matrix_ready_for_confirmation_plus_explicit_code_writes(monkeypatch):
    # EXPLICIT_READY_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.matrixD1", text=_PRODUCTION_CMON_TEXT))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.matrixD2", text="Ya"))  # -> READY_FOR_CONFIRMATION
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"

    _post(_message_envelope(message_id="wamid.matrixD3", text=f"YA {code}"))

    assert len(cmon.rows) == 1
    assert repo.rows[0]["state"] == "CONFIRMED"


def test_state_matrix_confirmed_plus_repeated_explicit_code_is_idempotent(monkeypatch):
    # CONFIRMED_REPEAT_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.matrixE1", text=_PRODUCTION_CMON_TEXT))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.matrixE2", text="Ya"))
    _post(_message_envelope(message_id="wamid.matrixE3", text="Ya"))
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert len(cmon.rows) == 1

    response = _post(_message_envelope(message_id="wamid.matrixE4", text=f"YA {code}"))

    assert response.status_code == 200
    assert len(cmon.rows) == 1
    # Production hardening -- a CONFIRMED CMON row's explicit-code retry
    # now discloses the existing canonical code rather than the old
    # generic message (see the dedicated confirmed-retry tests below for
    # full coverage of this behavior).
    assert outbound.calls[-1] == (SENDER_A, f"Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: {cmon.rows[0]['condition_monitoring_reading_code']}")


@pytest.mark.parametrize("terminal_state", ["EXPIRED", "CANCELLED", "REJECTED"])
def test_state_matrix_terminal_states_reject_confirmation_no_write(monkeypatch, terminal_state):
    # TERMINAL_STATE_TEST.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id=f"wamid.matrixF1{terminal_state}", text=_PRODUCTION_CMON_TEXT))
    code = repo.rows[0]["confirmation_id"]
    repo.rows[0]["state"] = terminal_state  # simulate expiry/cancellation/rejection

    response = _post(_message_envelope(message_id=f"wamid.matrixF2{terminal_state}", text=f"YA {code}"))

    assert response.status_code == 200
    assert cmon.rows == []
    assert repo.rows[0]["state"] == terminal_state
    assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")


# --- Task A: confirmed WhatsApp CMON retry idempotency -----------------

def test_confirmed_cmon_explicit_retry_returns_existing_canonical_code(monkeypatch):
    # CONFIRMED_RETRY_TEST -- explicit confirmation-code retry against an
    # already-CONFIRMED CMON row must resolve, disclose the existing
    # canonical code, and never write a second canonical record.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.confretryA", text=_PRODUCTION_CMON_TEXT))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.confretryB", text="Ya"))  # answers missing-date question only
    _post(_message_envelope(message_id="wamid.confretryC", text="Ya"))  # final confirmation -- writes
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert len(cmon.rows) == 1
    canonical_code = cmon.rows[0]["condition_monitoring_reading_code"]
    confirmed_by_before = repo.rows[0].get("confirmed_by")
    transition_calls_before = repo.transition_calls
    create_draft_calls_before = list(cmon.create_draft_calls)
    create_ad_hoc_draft_calls_before = list(cmon.create_ad_hoc_draft_calls)

    response = _post(_message_envelope(message_id="wamid.confretryD", text=f"YA {code}"))

    assert response.status_code == 200
    # Requirement 4: existing canonical code disclosed.
    assert outbound.calls[-1] == (SENDER_A, f"Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: {canonical_code}")
    # Requirement 2/6: canonical writer never invoked again, count stays 1.
    assert cmon.create_draft_calls == create_draft_calls_before
    assert cmon.create_ad_hoc_draft_calls == create_ad_hoc_draft_calls_before
    assert len(cmon.rows) == 1
    # Requirement 5: no re-CONFIRMATION transition -- confirmed_by (and by
    # construction, confirmed_at) unchanged. The one extra transition_calls
    # increment is _send_outbound_reply's own pre-existing, unrelated
    # last_outbound_provider_message_id correlation bookkeeping (fires
    # after every reply, confirmed_by=None, so it never touches
    # confirmed_by/confirmed_at) -- not a second confirmation.
    assert repo.transition_calls == transition_calls_before + 1
    assert repo.rows[0].get("confirmed_by") == confirmed_by_before
    assert repo.rows[0]["state"] == "CONFIRMED"


def test_confirmed_cmon_pm_retry_keeps_generic_message(monkeypatch):
    # PM_CHANGE=ZERO -- a CONFIRMED PM row's retry (no cmon_repository
    # match, detected_domain != CONDITION_MONITORING) keeps the original
    # generic reply, unaffected by the CMON-specific disclosure branch.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound)  # no cmon_repository -- matches PM's real wiring

    _post(_message_envelope(message_id="wamid.pmretryA", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"))
    code = repo.rows[0]["confirmation_id"]
    _post(_message_envelope(message_id="wamid.pmretryB", text="YA"))
    assert repo.rows[0]["state"] == "CONFIRMED"

    response = _post(_message_envelope(message_id="wamid.pmretryC", text=f"YA {code}"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Data sudah dikonfirmasi.")


def test_confirmed_cmon_plain_ya_does_not_select_confirmed_row(monkeypatch):
    # PLAIN_YA_SELECTION_TEST -- after a CMON row is CONFIRMED, a plain,
    # unlinked "Ya" with no other open pending must never re-select it
    # (find_actionable_pending_list already excludes CONFIRMED; this
    # proves the confirmed-retry disclosure branch above doesn't change
    # that guarantee).
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.plainyaA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.plainyaB", text="Ya"))
    _post(_message_envelope(message_id="wamid.plainyaC", text="Ya"))
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert len(cmon.rows) == 1

    response = _post(_message_envelope(message_id="wamid.plainyaD", text="Ya"))

    assert response.status_code == 200
    assert len(cmon.rows) == 1  # no second write, no resurrection
    assert outbound.calls[-1] == (SENDER_A, "Tidak ada data yang menunggu konfirmasi.")


# --- WhatsApp explicit confirmation routing bug investigation -----------
#
# Investigation result: no parsing/routing defect was found in
# whatsapp_intake_service.py for the exact reported production message.
# _CONFIRMATION_CODE_PATTERN.search() correctly extracts the WA-CONF
# token from "YA WA-CONF-<hex>" (verified directly, and via the tests
# below, entering through the SAME public webhook route production
# uses); "ya" is in _ACTION_WORDS regardless of case
# (tokens[0].casefold()); find_pending_by_confirmation_id's real SQL
# (whatsapp_intake_repository.py) has no state filter, matching the
# Fake used here; migration 030's confirmation_id DEFAULT
# ('WA-CONF-' || replace(gen_random_uuid()::text, '-', '')) produces
# exactly the lowercase, unhyphenated hex shape in the production
# evidence, so there is no case/format mismatch either. These tests use
# the EXACT literal production text (not a variable-built string) with
# the production intake_id/confirmation_id/canonical code hardcoded, to
# remove any doubt.

def _seed_confirmed_cmon_matching_production(monkeypatch):
    # Drives the normal 3-message flow, then overwrites the generated
    # confirmation_id/canonical code to the EXACT production values so
    # the literal-text tests below are a byte-for-byte reproduction of
    # the reported incident, not an approximation.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon)

    _post(_message_envelope(message_id="wamid.routingA", text=_PRODUCTION_CMON_TEXT))
    _post(_message_envelope(message_id="wamid.routingB", text="Ya"))
    _post(_message_envelope(message_id="wamid.routingC", text="Ya"))
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert len(cmon.rows) == 1

    repo.rows[0]["intake_id"] = "06501e02-60bf-4a2d-bc2b-9c750a0289a8"
    repo.rows[0]["confirmation_id"] = "WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a"
    cmon.rows[0]["condition_monitoring_reading_code"] = "CMONR-4B33E52CA2B5"
    cmon.rows[0]["source_reference"] = "WHATSAPP::06501e02-60bf-4a2d-bc2b-9c750a0289a8"
    return repo, outbound, cmon


def test_exact_production_message_explicit_confirmed_retry(monkeypatch):
    # EXACT_PRODUCTION_MESSAGE_TEST -- the literal reported text, entering
    # through the same public FastAPI webhook route production uses.
    # Starts from: one CONFIRMED CMON intake, canonical CMON already
    # exists, zero open pending confirmations (all three states hold
    # after _seed_confirmed_cmon_matching_production above).
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    confirmed_by_before = repo.rows[0].get("confirmed_by")
    transition_calls_before = repo.transition_calls
    create_draft_calls_before = list(cmon.create_draft_calls)
    create_ad_hoc_draft_calls_before = list(cmon.create_ad_hoc_draft_calls)

    response = _post(_message_envelope(
        message_id="wamid.exactprod",
        text="YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a",
    ))

    assert response.status_code == 200
    assert outbound.calls[-1] == (
        SENDER_A,
        "Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: CMONR-4B33E52CA2B5",
    )
    # canonical_count remains exactly 1; no canonical create method called.
    assert len(cmon.rows) == 1
    assert cmon.create_draft_calls == create_draft_calls_before
    assert cmon.create_ad_hoc_draft_calls == create_ad_hoc_draft_calls_before
    # confirmed_at/confirmed_by unchanged; no pending state transition (the
    # +1 is _send_outbound_reply's own pre-existing, unrelated
    # last_outbound_provider_message_id correlation bookkeeping).
    assert repo.transition_calls == transition_calls_before + 1
    assert repo.rows[0].get("confirmed_by") == confirmed_by_before
    assert repo.rows[0]["state"] == "CONFIRMED"


@pytest.mark.parametrize(
    "text",
    [
        "YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a",
        "Ya WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a",
        "ya WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a",
    ],
    ids=["upper", "title", "lower"],
)
def test_explicit_confirmed_retry_case_variants(monkeypatch, text):
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)

    response = _post(_message_envelope(message_id=f"wamid.case{text[:2]}", text=text))

    assert response.status_code == 200
    assert outbound.calls[-1] == (
        SENDER_A,
        "Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: CMONR-4B33E52CA2B5",
    )
    assert len(cmon.rows) == 1


def test_trailing_description_form_extracts_only_the_code(monkeypatch):
    # TRAILING_DESCRIPTION_TEST -- a trailing ": <description>" after the
    # WA-CONF token (a form that previously existed in production) must
    # continue extracting only the code, never rejected as unrecognized.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)

    response = _post(_message_envelope(
        message_id="wamid.trailingdesc",
        text="YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a: CONDITION_MONITORING 211-P-13AR",
    ))

    assert response.status_code == 200
    assert outbound.calls[-1] == (
        SENDER_A,
        "Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: CMONR-4B33E52CA2B5",
    )
    assert len(cmon.rows) == 1


@pytest.mark.parametrize("terminal_state", ["EXPIRED", "CANCELLED", "REJECTED"])
def test_exact_production_code_shape_terminal_state_never_resurrects(monkeypatch, terminal_state):
    # TERMINAL_STATE_GUARD -- same production-shaped confirmation_id, but
    # a terminal (not CONFIRMED) row must still be rejected, never
    # resurrected, regardless of the code's exact shape.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    repo.rows[0]["state"] = terminal_state

    response = _post(_message_envelope(
        message_id=f"wamid.termprod{terminal_state}",
        text="YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a",
    ))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Kode konfirmasi tidak ditemukan.")
    assert repo.rows[0]["state"] == terminal_state
    assert len(cmon.rows) == 1  # the pre-existing canonical row, untouched


def test_plain_ya_still_searches_open_states_only_with_production_shaped_row(monkeypatch):
    # PLAIN_YA_GUARD -- re-confirms, with the exact production row shape,
    # that a plain "Ya" (no code) never re-selects the CONFIRMED row.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)

    response = _post(_message_envelope(message_id="wamid.plainprod", text="Ya"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Tidak ada data yang menunggu konfirmasi.")
    assert len(cmon.rows) == 1


# --- Production diagnostic instrumentation ------------------------------

def test_confirmation_selection_diagnostic_log_explicit_confirmed_retry(monkeypatch, caplog):
    # Explicit-code retry against a CONFIRMED row: exactly one
    # event=whatsapp_confirmation_selection line, with the correct
    # explicit-lookup fields and no broad lookup attempted.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)

    with caplog.at_level("INFO"):
        response = _post(_message_envelope(
            message_id="wamid.diaglog1",
            text="YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a",
        ))
    assert response.status_code == 200

    selection_lines = [
        record.getMessage() for record in caplog.records
        if record.getMessage().startswith("event=whatsapp_confirmation_selection")
    ]
    assert len(selection_lines) == 1
    line = selection_lines[0]
    assert "action=ya" in line
    assert "selector_present=True" in line
    assert "explicit_lookup_attempted=True" in line
    assert "explicit_lookup_found=True" in line
    assert "explicit_lookup_state=CONFIRMED" in line
    assert "broad_lookup_attempted=False" in line
    assert "broad_candidate_count=None" in line
    assert "result_code=DUPLICATE_CONFIRMATION_CMON_RECORDED" in line

    # Never the plaintext confirmation_id, raw user_id, or phone number.
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a" not in log_text
    assert "44216d8d-a0d2-4a5f-8c00-34fac69cf82c" not in log_text
    assert "user-1" not in log_text
    assert "15550000001" not in log_text


def test_confirmation_selection_diagnostic_log_broad_no_pending(monkeypatch, caplog):
    # Plain "Ya" with zero open pending: broad lookup attempted, explicit
    # lookup never attempted.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)

    with caplog.at_level("INFO"):
        _post(_message_envelope(message_id="wamid.diaglog2", text="Ya"))

    selection_lines = [
        record.getMessage() for record in caplog.records
        if record.getMessage().startswith("event=whatsapp_confirmation_selection")
    ]
    assert len(selection_lines) == 1
    line = selection_lines[0]
    assert "explicit_lookup_attempted=False" in line
    assert "explicit_lookup_found=False" in line
    assert "explicit_lookup_state=None" in line
    assert "broad_lookup_attempted=True" in line
    assert "broad_candidate_count=0" in line
    assert "result_code=NO_PENDING_CONFIRMATION" in line


def test_confirmation_selection_diagnostic_log_unknown_code(monkeypatch, caplog):
    # A code that doesn't exist at all: explicit lookup attempted but not
    # found, broad lookup never reached (early return).
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)

    with caplog.at_level("INFO"):
        _post(_message_envelope(message_id="wamid.diaglog3", text="YA WA-CONF-000000000000000000000000000000ff"))

    selection_lines = [
        record.getMessage() for record in caplog.records
        if record.getMessage().startswith("event=whatsapp_confirmation_selection")
    ]
    assert len(selection_lines) == 1
    line = selection_lines[0]
    assert "explicit_lookup_attempted=True" in line
    assert "explicit_lookup_found=False" in line
    assert "explicit_lookup_state=None" in line
    assert "broad_lookup_attempted=False" in line
    assert "result_code=UNKNOWN_CONFIRMATION_ID" in line


# --- WhatsApp explicit-selector Unicode character-class diagnostic ------
#
# TEMPORARY diagnostic (see _log_confirmation_remainder_diagnostic in
# whatsapp_intake_service.py) for the still-open "selector_present=False
# despite a visually-ASCII message" production question. These tests
# prove the diagnostic itself correctly identifies plausible look-alike
# character classes -- they do NOT claim any one of these is the actual
# production cause, since no raw production message bytes are available
# to confirm that. No normalization fix is implemented here: the mission
# gates that on conclusive evidence, which does not yet exist.

def _diagnostic_lines(caplog):
    return [
        record.getMessage() for record in caplog.records
        if record.getMessage().startswith("event=whatsapp_confirmation_remainder_diagnostic")
    ]


def test_remainder_diagnostic_clean_ascii_reports_no_anomalies(monkeypatch, caplog):
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)

    with caplog.at_level("INFO"):
        _post(_message_envelope(message_id="wamid.udiagA", text="YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a"))

    lines = _diagnostic_lines(caplog)
    assert len(lines) == 1
    line = lines[0]
    assert "starts_with_expected_ascii_prefix=True" in line
    assert "contains_ascii_wa_conf=True" in line
    assert "nfkc_changes_input=False" in line
    assert "whitespace_codepoints=[]" in line
    assert "dash_like_codepoints=['0x2d']" in line
    assert "zero_width_codepoints=[]" in line


def test_remainder_diagnostic_detects_unicode_dash_variant(monkeypatch, caplog):
    # HYPHEN (U+2010) instead of HYPHEN-MINUS (U+002D) -- visually near-
    # identical in most UI fonts, but the regex's literal "-" won't match
    # it. A plausible source: mobile keyboard "smart punctuation"/
    # autocorrect substituting typed hyphens outside a recognized code/
    # URL field.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    text = "YA WA‐CONF‐f02afd2db6e94b9d9cb20e3cef2ac33a"

    with caplog.at_level("INFO"):
        response = _post(_message_envelope(message_id="wamid.udiagB", text=text))

    assert response.status_code == 200
    lines = _diagnostic_lines(caplog)
    assert len(lines) == 1
    line = lines[0]
    assert "starts_with_expected_ascii_prefix=False" in line
    assert "contains_ascii_wa_conf=False" in line
    assert "0x2010" in line  # dash_like_codepoints

    # Reproduces the exact production symptom for this character class:
    # selector never extracted, falls through to broad discovery, and
    # (with zero open pending here) NO_PENDING_CONFIRMATION.
    selection_line = next(
        r.getMessage() for r in caplog.records if r.getMessage().startswith("event=whatsapp_confirmation_selection")
    )
    assert "selector_present=False" in selection_line
    assert "explicit_lookup_attempted=False" in selection_line
    assert "result_code=NO_PENDING_CONFIRMATION" in selection_line

    # Never the plaintext code, even for a non-matching, diagnostic-only path.
    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "f02afd2db6e94b9d9cb20e3cef2ac33a" not in log_text


def test_remainder_diagnostic_mid_hex_break_fails_cleanly(monkeypatch, caplog):
    # Strict-32-hex fix -- the {32} fixed count plus trailing negative
    # lookahead means an invisible character landing INSIDE the hex
    # portion now correctly fails the WHOLE match (never a truncated
    # partial selector, unlike the old unbounded [0-9A-Fa-f]+). No other
    # pending is open here, so this falls through to plain-YA broad
    # discovery and NO_PENDING_CONFIRMATION -- production's exact
    # symptom, and a strictly better outcome than accepting a wrong,
    # truncated selector.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    text = "YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a".replace("f02afd2d", "f02afd2d​")

    with caplog.at_level("INFO"):
        _post(_message_envelope(message_id="wamid.udiagC", text=text))

    diag_line = _diagnostic_lines(caplog)[0]
    assert "0x200b" in diag_line  # zero_width_codepoints
    assert "whitespace_codepoints=[]" in diag_line  # confirms it is NOT whitespace-classified

    selection_line = next(
        r.getMessage() for r in caplog.records if r.getMessage().startswith("event=whatsapp_confirmation_selection")
    )
    assert "selector_present=False" in selection_line
    assert "explicit_lookup_attempted=False" in selection_line
    assert "result_code=NO_PENDING_CONFIRMATION" in selection_line


def test_remainder_diagnostic_internal_nbsp_also_fails_cleanly(monkeypatch, caplog):
    # Same point as above, for NO-BREAK SPACE (U+00A0) landing inside the
    # hex portion instead.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    text = "YA WA-CONF-f02afd2d b6e94b9d9cb20e3cef2ac33a"

    with caplog.at_level("INFO"):
        _post(_message_envelope(message_id="wamid.udiagD", text=text))

    diag_line = _diagnostic_lines(caplog)[0]
    assert "0xa0" in diag_line  # whitespace_codepoints
    assert "starts_with_expected_ascii_prefix=True" in diag_line  # prefix itself is clean ASCII

    selection_line = next(
        r.getMessage() for r in caplog.records if r.getMessage().startswith("event=whatsapp_confirmation_selection")
    )
    assert "selector_present=False" in selection_line
    assert "explicit_lookup_attempted=False" in selection_line
    assert "result_code=NO_PENDING_CONFIRMATION" in selection_line


def test_remainder_diagnostic_fullwidth_hyphen_normalizes_under_nfkc(monkeypatch, caplog):
    # FULLWIDTH HYPHEN-MINUS (U+FF0D) -- unlike most dash look-alikes,
    # this one IS resolved by NFKC compatibility normalization, so
    # nfkc_changes_input=True specifically flags this class as
    # recoverable without weakening WA-CONF+32-hex validation.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    text = "YA WA－CONF－f02afd2db6e94b9d9cb20e3cef2ac33a"

    with caplog.at_level("INFO"):
        _post(_message_envelope(message_id="wamid.udiagE", text=text))

    lines = _diagnostic_lines(caplog)
    assert len(lines) == 1
    line = lines[0]
    assert "nfkc_changes_input=True" in line
    assert "0xff0d" in line  # dash_like_codepoints


def test_remainder_diagnostic_never_logs_plaintext_across_all_variants(monkeypatch, caplog):
    # Cross-cutting privacy check across every character-class variant
    # above, in one place.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    variants = [
        "YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a",
        "YA WA‐CONF‐f02afd2db6e94b9d9cb20e3cef2ac33a",
        "YA WA-CONF-f02afd2d​b6e94b9d9cb20e3cef2ac33a",
        "YA WA-CONF-f02afd2d b6e94b9d9cb20e3cef2ac33a",
    ]
    with caplog.at_level("INFO"):
        for i, text in enumerate(variants):
            _post(_message_envelope(message_id=f"wamid.udiagF{i}", text=text))

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "f02afd2db6e94b9d9cb20e3cef2ac33a" not in log_text
    assert "f02afd2d" not in log_text
    assert "b6e94b9d9cb20e3cef2ac33a" not in log_text
    assert "44216d8d-a0d2-4a5f-8c00-34fac69cf82c" not in log_text
    assert "15550000001" not in log_text


# --- Prefix-only structural diagnostic (WA-CONF- casing candidate) ------
#
# Static-audit finding: _CONFIRMATION_CODE_PATTERN has no re.IGNORECASE
# flag, so its literal "WA-CONF-" prefix is case-sensitive (only the hex
# suffix's own [0-9A-Fa-f] character class already covers both cases).
# A lowercase or mixed-case remainder reproduces EVERY SINGLE field of
# the authoritative production evidence simultaneously (length=40, ASCII
# hyphens only, NFKC-unchanged, no whitespace, no zero-width chars,
# contains_ascii_wa_conf=False, starts_with_expected_ascii_prefix=False,
# selector_present=False) -- unlike the Unicode-dash hypothesis, which
# only explained a subset. Reported here as a candidate, not a proven
# cause: no raw production message bytes exist to confirm it. No parser
# fix is implemented -- diagnostics only, per instruction.

@pytest.mark.parametrize(
    "prefix,expected_codepoints,casefold_matches",
    [
        ("WA-CONF-", "['0x57', '0x41', '0x2d', '0x43', '0x4f', '0x4e', '0x46', '0x2d']", True),
        ("wa-conf-", "['0x77', '0x61', '0x2d', '0x63', '0x6f', '0x6e', '0x66', '0x2d']", True),
        ("Wa-Conf-", "['0x57', '0x61', '0x2d', '0x43', '0x6f', '0x6e', '0x66', '0x2d']", True),
    ],
    ids=["upper", "lower", "mixed"],
)
def test_prefix_diagnostic_codepoints_by_case(monkeypatch, caplog, prefix, expected_codepoints, casefold_matches):
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    text = f"YA {prefix}f02afd2db6e94b9d9cb20e3cef2ac33a"

    with caplog.at_level("INFO"):
        response = _post(_message_envelope(message_id=f"wamid.prefixdiag{prefix[:2]}", text=text))
    assert response.status_code == 200

    diag_line = _diagnostic_lines(caplog)[0]
    assert "prefix_length_inspected=8" in diag_line
    assert f"prefix_codepoints={expected_codepoints}" in diag_line
    assert f"prefix_casefold_matches_expected={casefold_matches}" in diag_line

    # Never the 32-hex identifier -- position 8 onward is never inspected.
    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "f02afd2db6e94b9d9cb20e3cef2ac33a" not in log_text
    assert "f02afd2d" not in log_text


def test_lowercase_prefix_now_resolves_correctly_exact_production_regression(monkeypatch, caplog):
    # THE FIX, proven against the exact production message: a lowercase
    # remainder used to reproduce every field of the production failure
    # (see 7ed0f95's diagnostic commit); with the case-insensitive
    # prefix + canonicalization fix, it now resolves exactly like the
    # uppercase form.
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    confirmed_by_before = repo.rows[0].get("confirmed_by")
    create_draft_calls_before = list(cmon.create_draft_calls)
    create_ad_hoc_draft_calls_before = list(cmon.create_ad_hoc_draft_calls)
    text = "YA wa-conf-f02afd2db6e94b9d9cb20e3cef2ac33a"

    with caplog.at_level("INFO"):
        response = _post(_message_envelope(message_id="wamid.lowercaseprod", text=text))
    assert response.status_code == 200

    diag_line = _diagnostic_lines(caplog)[0]
    assert "remainder_length=40" in diag_line
    assert "dash_like_codepoints=['0x2d']" in diag_line
    assert "zero_width_codepoints=[]" in diag_line
    assert "prefix_casefold_matches_expected=True" in diag_line

    selection_line = next(
        r.getMessage() for r in caplog.records if r.getMessage().startswith("event=whatsapp_confirmation_selection")
    )
    assert "selector_present=True" in selection_line
    assert "explicit_lookup_attempted=True" in selection_line
    assert "explicit_lookup_found=True" in selection_line
    assert "explicit_lookup_state=CONFIRMED" in selection_line
    assert "result_code=DUPLICATE_CONFIRMATION_CMON_RECORDED" in selection_line

    # Response says CMON already stored, includes the existing canonical
    # code -- not the old generic "Data sudah dikonfirmasi." or the
    # broken NO_PENDING_CONFIRMATION.
    assert outbound.calls[-1] == (
        SENDER_A,
        "Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: CMONR-4B33E52CA2B5",
    )
    # Zero canonical write, canonical count stays exactly 1, confirmed_at/
    # confirmed_by unchanged (no transition_pending call for confirmation
    # -- read-only lookup only).
    assert len(cmon.rows) == 1
    assert cmon.create_draft_calls == create_draft_calls_before
    assert cmon.create_ad_hoc_draft_calls == create_ad_hoc_draft_calls_before
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert repo.rows[0].get("confirmed_by") == confirmed_by_before


# --- Strict 32-hex + case-insensitive-prefix boundary matrix ------------

@pytest.mark.parametrize(
    "text,should_resolve",
    [
        ("YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33a", True),
        ("YA wa-conf-f02afd2db6e94b9d9cb20e3cef2ac33a", True),
        ("YA Wa-Conf-f02afd2db6e94b9d9cb20e3cef2ac33a", True),
        ("YA WA-CONF-F02AFD2DB6E94B9D9CB20E3CEF2AC33A", True),
        ("YA wa-conf-F02AFD2DB6E94B9D9CB20E3CEF2AC33A", True),
        ("YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33", False),
        ("YA WA-CONF-f02afd2db6e94b9d9cb20e3cef2ac33aa", False),
        ("YA WA-CONF-zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz", False),
        ("YA WA‐CONF‐f02afd2db6e94b9d9cb20e3cef2ac33a", False),
    ],
    ids=[
        "upper_prefix_lower_hex", "lower_prefix_lower_hex", "mixed_prefix_lower_hex",
        "upper_prefix_upper_hex", "lower_prefix_upper_hex",
        "31_hex_reject", "33_hex_reject", "non_hex_reject", "unicode_dash_prefix_reject",
    ],
)
def test_selector_strict_boundary_matrix(monkeypatch, text, should_resolve):
    repo, outbound, cmon = _seed_confirmed_cmon_matching_production(monkeypatch)
    create_draft_calls_before = list(cmon.create_draft_calls)
    create_ad_hoc_draft_calls_before = list(cmon.create_ad_hoc_draft_calls)

    response = _post(_message_envelope(message_id=f"wamid.boundary{abs(hash(text))}", text=text))

    assert response.status_code == 200
    if should_resolve:
        assert outbound.calls[-1] == (
            SENDER_A,
            "Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: CMONR-4B33E52CA2B5",
        )
    else:
        # Falls through to plain-YA broad discovery (zero open pending
        # here), never accepted as a fuzzy/partial match, never a second
        # canonical write, never a false "found" response.
        assert outbound.calls[-1] == (SENDER_A, "Tidak ada data yang menunggu konfirmasi.")
    assert len(cmon.rows) == 1
    assert cmon.create_draft_calls == create_draft_calls_before
    assert cmon.create_ad_hoc_draft_calls == create_ad_hoc_draft_calls_before
    assert repo.rows[0]["state"] == "CONFIRMED"


# --- MWO: PRODUCTION READINESS + WHATSAPP -> LTSA AI INTEGRATION AUDIT, ------
# Phase 11 -- WhatsApp -> LTSA AI query routing. Reuses the exact same
# LTSAAIQueryDependencies bundle / orchestrate_copilot / ask_copilot
# machinery routers/copilot.py's own dashboard endpoint already depends on
# -- no new gateway, no duplicated business logic. All tests below use
# ai_client=None (no LLM configured) unless the test is specifically
# exercising the AI-error/malformed-response fallback, since orchestrate_
# copilot's own deterministic fallback IS the AI-less production behavior
# today (dependencies.get_copilot_ai_client() only returns a client when a
# provider env var is configured).


class _FakeWorkOrderGateway:
    def __init__(self, work_orders):
        self._work_orders = work_orders

    def list_work_orders(self):
        return {"success": True, "data": self._work_orders}


class _PoisonLTSAAIGateway:
    # Raises instead of returning inert data -- proves a deterministic
    # PM/CMON command NEVER reaches the LTSA AI query path at all (not
    # merely that it produces a harmless answer). Any attribute access
    # (not just a call) already indicates the routing gate was bypassed.
    def __getattr__(self, name):
        raise AssertionError(
            f"LTSA AI query path must not be reached for a deterministic PM/CMON command (accessed .{name})"
        )


class _PoisonAIClient:
    def generate_json(self, *args, **kwargs):
        raise AssertionError("LTSA AI query path must not be reached for a deterministic PM/CMON command")


def _poison_ltsa_ai_query_deps():
    from API.whatsapp_intake_service import LTSAAIQueryDependencies
    return LTSAAIQueryDependencies(
        ai_client=_PoisonAIClient(),
        maintenance_history_gateway=_PoisonLTSAAIGateway(),
        work_order_gateway=_PoisonLTSAAIGateway(),
        installation_gateway=_PoisonLTSAAIGateway(),
        ltsa_knowledge_service=_PoisonLTSAAIGateway(),
        equipment_timeline_service=_PoisonLTSAAIGateway(),
        condition_monitoring_reading_gateway=_PoisonLTSAAIGateway(),
        installation_report_repository=_PoisonLTSAAIGateway(),
        mechanical_seal_stock_repository=_PoisonLTSAAIGateway(),
        condition_monitoring_reading_repository=_PoisonLTSAAIGateway(),
        fleet_executive_summary_service=_PoisonLTSAAIGateway(),
    )


class _RaisingAIClient:
    # Simulates an AI provider timeout/error -- orchestrate_copilot's own
    # try/except must catch this and fall back to the deterministic
    # dispatcher, never surface a 500 to the WhatsApp caller.
    def generate_json(self, *args, **kwargs):
        raise TimeoutError("simulated AI provider timeout")


class _MalformedToolSelectionAIClient:
    # Simulates a configured AI provider returning a response that doesn't
    # match the expected {"tools": [...]} shape -- _select_tools must treat
    # this as "no tools selected" and fall back to the deterministic
    # dispatcher, never raise.
    def generate_json(self, *args, **kwargs):
        return {"unexpected_field": "not a tools list"}


def _query_deps(
    *,
    ai_client=None,
    pump_gateway=None,
    work_order_gateway=None,
    mechanical_seal_stock_repository=None,
    condition_monitoring_reading_gateway=None,
    condition_monitoring_reading_repository=None,
    fleet_executive_summary_service=None,
):
    from API.whatsapp_intake_service import LTSAAIQueryDependencies
    return LTSAAIQueryDependencies(
        ai_client=ai_client,
        maintenance_history_gateway=_InertLTSAAIGateway(),
        work_order_gateway=work_order_gateway or _InertLTSAAIGateway(),
        installation_gateway=_InertLTSAAIGateway(),
        ltsa_knowledge_service=_InertLTSAAIGateway(),
        equipment_timeline_service=_InertLTSAAIGateway(),
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway or _InertLTSAAIGateway(),
        installation_report_repository=_InertLTSAAIGateway(),
        mechanical_seal_stock_repository=mechanical_seal_stock_repository or _InertLTSAAIGateway(),
        condition_monitoring_reading_repository=condition_monitoring_reading_repository or _InertLTSAAIGateway(),
        fleet_executive_summary_service=fleet_executive_summary_service or _InertLTSAAIGateway(),
    )


_PUMP_STATUS_ANSWER = (
    "211-P-13AR (unknown type) is currently UNKNOWN, located at an unknown "
    "location in area HOC.\n\nSource: LTSA canonical data (FACT)"
)


def test_natural_language_pump_status_query_answers_via_ltsa_ai(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps())

    response = _post(_message_envelope(message_id="wamid.qstatus", text="Apa status pompa 211-P-13AR?"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, _PUMP_STATUS_ANSWER)
    # Read-only: a question never persists a pending intake row, unlike
    # PM/CMON's own two-step confirmation flow.
    assert repo.rows == []


def test_work_orders_query_answers_via_ltsa_ai_and_never_persists_pending_row(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    wo_gateway = _FakeWorkOrderGateway([
        {"work_order_code": "WO-1001", "asset_code": "211-P-13AR", "status": "OPEN", "assigned_to": "tech-1", "closed_at": None},
    ])
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(work_order_gateway=wo_gateway))

    response = _post(_message_envelope(message_id="wamid.qwo", text="Ada work order aktif untuk 211-P-13AR?"))

    assert response.status_code == 200
    reply = outbound.calls[-1][1]
    assert "WO-1001" in reply
    assert "Source: LTSA canonical data (FACT)" in reply
    assert repo.rows == []


def test_tag_scoped_condition_monitoring_query_is_graceful_data_gap_not_a_crash(monkeypatch):
    # Regression for the pre-existing copilot_ask_service.py KeyError bug
    # (TOOL_HANDLERS originally had no per-asset "condition_monitoring"
    # entry) -- this text contains "kebocoran" (leak), which is the exact
    # word that would otherwise raise an unhandled KeyError and produce no
    # reply at all. condition_monitoring now has a real per-asset handler
    # (MWO: CLOSE FINAL LTSA AI WHATSAPP QUERY GAPS), so with the default
    # inert (non-list) repository stub this is a truthful "data
    # unavailable" DATA_GAP, not a crash -- the property under test is
    # "never crashes", not the specific wording.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps())

    response = _post(_message_envelope(message_id="wamid.qcmon", text="Apakah ada kebocoran di 211-P-13AR?"))

    assert response.status_code == 200
    reply = outbound.calls[-1][1]
    assert "currently unavailable" in reply
    assert repo.rows == []


def test_query_with_no_available_data_is_truthful_data_gap(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    # Default _InertLTSAAIGateway work_order_gateway -> {"success": False}.
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps())

    response = _post(_message_envelope(message_id="wamid.qgap", text="Ada work order aktif untuk 211-P-13AR?"))

    assert response.status_code == 200
    reply = outbound.calls[-1][1]
    assert "currently unavailable" in reply
    assert "Source:" not in reply  # DATA_GAP with no evidence -> no footer, never a fabricated source.
    assert repo.rows == []


def test_query_for_unknown_pump_tag_is_rejected_with_generic_message(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps())

    response = _post(_message_envelope(message_id="wamid.qunknown", text="Apa status pompa 999-P-99AR?"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Pump 999-P-99AR tidak ditemukan.")
    assert repo.rows == []


def test_query_for_out_of_scope_pump_tag_is_rejected_with_same_generic_message_as_unknown(monkeypatch):
    # Phase 7: an out-of-scope real pump must produce the EXACT same
    # generic reply as a nonexistent tag -- never a distinct status that
    # would leak "this pump exists but you can't see it" to an
    # unauthorized caller.
    repo = FakeIntakeRepository({SENDER_A: _out_of_scope_identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps())

    response = _post(_message_envelope(message_id="wamid.qoutscope", text="Apa status pompa 211-P-13AR?"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Pump 211-P-13AR tidak ditemukan.")
    assert repo.rows == []


def test_query_from_unregistered_phone_is_rejected_before_reaching_ltsa_ai(monkeypatch):
    # Auth gate runs before ANY routing decision -- an unknown sender must
    # never receive LTSA data, and the LTSA AI path must never even be
    # touched (proven via the poison deps, not just a benign inert stub).
    repo = FakeIntakeRepository({})  # SENDER_A registers no identity
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_poison_ltsa_ai_query_deps())

    response = _post(_message_envelope(message_id="wamid.qunauth", text="Apa status pompa 211-P-13AR?"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Nomor WhatsApp belum terdaftar.")
    assert repo.rows == []


def test_ai_provider_timeout_falls_back_to_deterministic_answer_not_500(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(ai_client=_RaisingAIClient()))

    response = _post(_message_envelope(message_id="wamid.qaierr", text="Apa status pompa 211-P-13AR?"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, _PUMP_STATUS_ANSWER)


def test_malformed_ai_tool_selection_falls_back_to_deterministic_answer(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(ai_client=_MalformedToolSelectionAIClient()))

    response = _post(_message_envelope(message_id="wamid.qaimalformed", text="Apa status pompa 211-P-13AR?"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, _PUMP_STATUS_ANSWER)


def test_deterministic_pm_command_never_reaches_ltsa_ai_path(monkeypatch):
    # _PRODUCTION_PM_TEXT ("PM 211-P-13AR ganti oli mesin") contains "PM"
    # and "ganti", both of which copilot_ask_service's OWN classifier would
    # also recognize (as "pm"/"installation") if this ever reached it --
    # the poison deps prove the SUPPORTED_INTENTS gate, not just that the
    # answer happens to look like a normal PM confirmation.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    pm = FakePMOccurrenceRepository()
    _wire(monkeypatch, repo, outbound, pm_repository=pm, ltsa_ai_query_deps=_poison_ltsa_ai_query_deps())

    response = _post(_message_envelope(message_id="wamid.pmnotai", text=_PRODUCTION_PM_TEXT))

    assert response.status_code == 200
    assert repo.rows[0]["state"] in {"NEEDS_INFORMATION", "READY_FOR_CONFIRMATION"}
    assert repo.rows[0]["detected_domain"] == "PM"


def test_deterministic_cmon_command_never_reaches_ltsa_ai_path(monkeypatch):
    # _PRODUCTION_CMON_TEXT contains "kebocoran" (leak), which
    # copilot_ask_service's OWN classifier maps to "condition_monitoring"
    # if this ever reached it -- poison deps prove the gate holds.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon = FakeConditionMonitoringReadingRepository()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon, ltsa_ai_query_deps=_poison_ltsa_ai_query_deps())

    response = _post(_message_envelope(message_id="wamid.cmonnotai", text=_PRODUCTION_CMON_TEXT))

    assert response.status_code == 200
    assert repo.rows[0]["detected_domain"] == "CONDITION_MONITORING"


def test_repeated_identical_query_delivery_is_idempotent_and_read_only(monkeypatch):
    # A query never persists a pending row (unlike PM/CMON), so a
    # duplicate webhook delivery of the exact same provider_message_id has
    # no state to collide with -- it simply answers again, read-only, both
    # times. Proves no duplicate side effect can accumulate even without
    # the PM/CMON DUPLICATE_DELIVERY mechanism applying here.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps())

    envelope = _message_envelope(message_id="wamid.qdupe", text="Apa status pompa 211-P-13AR?")
    first = _post(envelope)
    second = _post(envelope)

    assert first.status_code == 200
    assert second.status_code == 200
    assert outbound.calls[0] == (SENDER_A, _PUMP_STATUS_ANSWER)
    assert outbound.calls[1] == (SENDER_A, _PUMP_STATUS_ANSWER)
    assert repo.rows == []


# --- MWO: CLOSE FINAL LTSA AI WHATSAPP QUERY GAPS -------------------------
#
# Phase 1 (tag-scoped Condition Monitoring) and Phase 2 (fleet priority)
# through the real webhook, proving both new capabilities reuse the exact
# same canonical repository/service the CMON WRITE flow and the dashboard's
# /api/ltsa/fleet/powerbi endpoint already use -- no new gateway, no
# duplicated scoring/business logic.


class _FakeQueryCMONRepository:
    def __init__(self, readings_by_asset=None):
        self._readings_by_asset = readings_by_asset or {}

    def list_by_asset(self, asset_code):
        return list(self._readings_by_asset.get(asset_code, []))


class _FakeTopRisk:
    def __init__(self, tag_number, title, priority, action):
        self.tag_number = tag_number
        self.title = title
        self.priority = priority
        self.action = action


class _FakeFleetExecutiveSummary:
    def __init__(self, *, fleet_status="ATTENTION", top_risks=()):
        self.fleet_status = fleet_status
        self.top_risks = top_risks


class _FakeFleetExecutiveSummaryService:
    def __init__(self, summary=None, *, raises=False):
        self._summary = summary if summary is not None else _FakeFleetExecutiveSummary(fleet_status="NORMAL", top_risks=())
        self._raises = raises
        self.build_calls = []

    def build(self, *, scope=None):
        self.build_calls.append(scope)
        if self._raises:
            raise RuntimeError("simulated fleet reliability service failure")
        return self._summary


# --- CMON query scenarios (mission Phase 5, items 1-7) --------------------


def test_cmon_query_returns_latest_reading_for_authorized_known_pump(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon_query_repo = _FakeQueryCMONRepository({
        "211-P-13AR": [
            {"condition_monitoring_reading_code": "CMONR-1", "reading_date": "2026-08-30", "finding": "Kebocoran mechanical seal"},
        ]
    })
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(condition_monitoring_reading_repository=cmon_query_repo))

    response = _post(_message_envelope(message_id="wamid.cmonq1", text="Ada temuan terbaru di 211-P-13AR?"))

    assert response.status_code == 200
    reply = outbound.calls[-1][1]
    assert "CMON terakhir: 2026-08-30" in reply
    assert "Temuan: Kebocoran mechanical seal" in reply
    assert repo.rows == []


def test_cmon_query_multiple_records_selects_newest(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon_query_repo = _FakeQueryCMONRepository({
        "211-P-13AR": [
            {"condition_monitoring_reading_code": "CMONR-NEWEST", "reading_date": "2026-08-30", "finding": "Newest finding"},
            {"condition_monitoring_reading_code": "CMONR-OLDER", "reading_date": "2026-01-01", "finding": "Older finding"},
        ]
    })
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(condition_monitoring_reading_repository=cmon_query_repo))

    response = _post(_message_envelope(message_id="wamid.cmonq2", text="CMON terakhir 211-P-13AR apa?"))

    reply = outbound.calls[-1][1]
    assert "Newest finding" in reply
    assert "Older finding" not in reply


def test_cmon_query_no_data_is_clear_no_data_response(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(condition_monitoring_reading_repository=_FakeQueryCMONRepository()))

    response = _post(_message_envelope(message_id="wamid.cmonq3", text="Ada temuan terbaru di 211-P-13AR?"))

    assert response.status_code == 200
    reply = outbound.calls[-1][1]
    # kind=FACT (a confirmed, truthful "nothing exists"), so the reply
    # carries the usual Source footer -- only a DATA_GAP with no evidence
    # suppresses it (_format_ltsa_ai_reply's own rule).
    assert reply.startswith("Belum ada data Condition Monitoring untuk 211-P-13AR.")
    assert repo.rows == []


def test_cmon_query_unknown_pump_rejected_generic_message(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps())

    response = _post(_message_envelope(message_id="wamid.cmonq4", text="Ada temuan terbaru di 999-P-99AR?"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Pump 999-P-99AR tidak ditemukan.")


def test_cmon_query_out_of_scope_pump_rejected_same_generic_message(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _out_of_scope_identity()})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps())

    response = _post(_message_envelope(message_id="wamid.cmonq5", text="Ada temuan terbaru di 211-P-13AR?"))

    assert response.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, "Pump 211-P-13AR tidak ditemukan.")


def test_cmon_query_missing_canonical_fields_never_invented(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon_query_repo = _FakeQueryCMONRepository({"211-P-13AR": [{"condition_monitoring_reading_code": "CMONR-BARE"}]})
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(condition_monitoring_reading_repository=cmon_query_repo))

    response = _post(_message_envelope(message_id="wamid.cmonq6", text="Ada temuan terbaru di 211-P-13AR?"))

    reply = outbound.calls[-1][1]
    assert "CMON terakhir: tidak diketahui" in reply
    assert "Temuan: tidak ada catatan" in reply
    assert "Status:" not in reply
    assert "Rekomendasi:" not in reply
    assert "Sumber:" not in reply


def test_cmon_query_never_persists_pending_row(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon_query_repo = _FakeQueryCMONRepository({"211-P-13AR": [{"condition_monitoring_reading_code": "CMONR-1", "finding": "x"}]})
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(condition_monitoring_reading_repository=cmon_query_repo))

    _post(_message_envelope(message_id="wamid.cmonq7", text="Ada temuan terbaru di 211-P-13AR?"))

    assert repo.rows == []


# --- Fleet priority scenarios (mission Phase 5, items 8-15) ----------------


def test_fleet_priority_query_reuses_canonical_ranking(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    summary = _FakeFleetExecutiveSummary(
        top_risks=(_FakeTopRisk("211-P-13AR", "Vibration trending high", 120, "Schedule CM inspection"),)
    )
    service = _FakeFleetExecutiveSummaryService(summary)
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(fleet_executive_summary_service=service))

    response = _post(_message_envelope(message_id="wamid.fleetq1", text="Pompa mana yang perlu perhatian hari ini?"))

    assert response.status_code == 200
    reply = outbound.calls[-1][1]
    assert "211-P-13AR" in reply
    assert "Vibration trending high" in reply
    assert repo.rows == []


def test_fleet_priority_ranking_order_preserved_never_recomputed(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    summary = _FakeFleetExecutiveSummary(
        top_risks=(
            _FakeTopRisk("211-P-13AR", "Low priority risk", 10, "Monitor"),
            _FakeTopRisk("210-P-05AR", "High priority risk", 200, "Escalate"),
        )
    )
    service = _FakeFleetExecutiveSummaryService(summary)
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(fleet_executive_summary_service=service))

    response = _post(_message_envelope(message_id="wamid.fleetq2", text="Pompa paling kritis apa?"))

    reply = outbound.calls[-1][1]
    assert reply.index("211-P-13AR") < reply.index("210-P-05AR")


def test_fleet_priority_query_authorization_scope_applied_before_result(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _out_of_scope_identity()})  # AREA=HSC
    outbound = FakeOutboundClient()
    service = _FakeFleetExecutiveSummaryService()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(fleet_executive_summary_service=service))

    _post(_message_envelope(message_id="wamid.fleetq3", text="Pompa paling kritis di area saya?"))

    assert service.build_calls == [frozenset({"HSC"})]


def test_fleet_priority_query_unrestricted_role_scope_is_none(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})  # TAP_ENGINEER, unrestricted
    outbound = FakeOutboundClient()
    service = _FakeFleetExecutiveSummaryService()
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(fleet_executive_summary_service=service))

    _post(_message_envelope(message_id="wamid.fleetq4", text="Pompa mana yang perlu perhatian hari ini?"))

    assert service.build_calls == [None]


def test_fleet_priority_no_actionable_assets_is_truthful_no_crash(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    service = _FakeFleetExecutiveSummaryService(_FakeFleetExecutiveSummary(fleet_status="NORMAL", top_risks=()))
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(fleet_executive_summary_service=service))

    response = _post(_message_envelope(message_id="wamid.fleetq5", text="Ada equipment yang perlu diperhatikan?"))

    assert response.status_code == 200
    assert "no pumps" in outbound.calls[-1][1].lower()


def test_fleet_priority_empty_fleet_is_truthful_no_crash(monkeypatch):
    # Same code path as "no actionable assets" (an empty fleet also has
    # zero top_risks) -- kept as its own test since the mission lists them
    # as distinct scenarios; copilot_ask_service's own unit tests already
    # distinguish the FACT-kind/DATA_GAP-kind boundary in detail.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    service = _FakeFleetExecutiveSummaryService(_FakeFleetExecutiveSummary(fleet_status="UNKNOWN", top_risks=()))
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(fleet_executive_summary_service=service))

    response = _post(_message_envelope(message_id="wamid.fleetq6", text="Prioritas pompa hari ini"))

    assert response.status_code == 200
    assert "no pumps" in outbound.calls[-1][1].lower()


def test_fleet_priority_service_failure_is_data_gap_not_a_crash(monkeypatch):
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    service = _FakeFleetExecutiveSummaryService(raises=True)
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(fleet_executive_summary_service=service))

    response = _post(_message_envelope(message_id="wamid.fleetq7", text="Pompa mana yang perlu perhatian hari ini?"))

    assert response.status_code == 200
    assert "unavailable" in outbound.calls[-1][1].lower()


def test_fleet_priority_malformed_service_result_never_crashes(monkeypatch):
    class _MalformedSummary:
        fleet_status = "ATTENTION"
        top_risks = None  # malformed: not a tuple

    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    service = _FakeFleetExecutiveSummaryService(_MalformedSummary())
    _wire(monkeypatch, repo, outbound, ltsa_ai_query_deps=_query_deps(fleet_executive_summary_service=service))

    response = _post(_message_envelope(message_id="wamid.fleetq8", text="Pompa mana yang perlu perhatian hari ini?"))

    assert response.status_code == 200
    assert "no pumps" in outbound.calls[-1][1].lower()


# --- Routing: the critical CMON write-vs-query ambiguity -------------------


def test_cmon_write_vs_query_ambiguity_resolved_correctly(monkeypatch):
    # The mission's own critical test: two messages both headed by "CMON"
    # must route to opposite paths -- a finding report is a transactional
    # write, a question about existing data is a read-only LTSA AI query.
    repo = FakeIntakeRepository({SENDER_A: _identity()})
    outbound = FakeOutboundClient()
    cmon_write_repo = FakeConditionMonitoringReadingRepository()
    cmon_query_repo = _FakeQueryCMONRepository({
        "211-P-13AR": [{"condition_monitoring_reading_code": "CMONR-1", "reading_date": "2026-08-30", "finding": "Kebocoran mechanical seal"}],
    })
    _wire(
        monkeypatch, repo, outbound, cmon_repository=cmon_write_repo,
        ltsa_ai_query_deps=_query_deps(condition_monitoring_reading_repository=cmon_query_repo),
    )

    write_response = _post(_message_envelope(message_id="wamid.ambigwrite", text="CMON 211-P-13AR: mechanical seal bocor"))
    assert write_response.status_code == 200
    assert repo.rows[0]["detected_domain"] == "CONDITION_MONITORING"
    assert repo.rows[0]["state"] in {"NEEDS_INFORMATION", "READY_FOR_CONFIRMATION"}

    query_response = _post(_message_envelope(message_id="wamid.ambigquery", text="CMON terakhir 211-P-13AR?"))
    assert query_response.status_code == 200
    reply = outbound.calls[-1][1]
    assert "CMON terakhir: 2026-08-30" in reply
    # The query must not have created a SECOND pending row.
    assert len(repo.rows) == 1

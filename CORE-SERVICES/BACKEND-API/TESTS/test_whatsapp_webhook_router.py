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
from dependencies import get_pump_gateway, get_whatsapp_intake_repository, get_whatsapp_outbound_client
from main import app

client = TestClient(app)

WEBHOOK_PATH = "/api/ltsa/whatsapp/webhook"


class FakePumpGateway:
    def __init__(self):
        self.pumps = {"211-P-13AR": {"tag_number": "211-P-13AR", "area": "HOC"}}

    def get_pump(self, tag_number):
        pump = self.pumps.get(tag_number)
        return {"success": bool(pump), "data": pump}


class FakeIntakeRepository:
    def __init__(self, identity=None):
        self.identity = identity
        self.rows = []

    def find_identity_by_sender_hash(self, sender_hash):
        expected = hash_sender_identifier(normalize_sender_identifier("+15550000001"))
        return self.identity if sender_hash == expected else None

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
        return None

    def find_latest_actionable_pending(self, sender_user_id):
        return None

    def create_pending(self, payload):
        row = {
            "intake_id": f"wa-{len(self.rows) + 1}",
            "confirmation_id": f"CONF-{len(self.rows) + 1}",
            "reply_text": payload.get("reply"),
            **payload,
        }
        self.rows.append(row)
        return row

    def transition_pending(self, intake_id, *, state, confirmed_by=None, validation_result=None):
        raise AssertionError("not exercised by webhook tests")


class FakeOutboundClient:
    def __init__(self, *, raises: bool = False):
        self.calls: list[tuple[str, str]] = []
        self._raises = raises

    def send_text(self, recipient, text):
        self.calls.append((recipient, text))
        if self._raises:
            raise RuntimeError("simulated provider failure")
        return OutboundResult(status="SUCCESS", http_status=200)


def _identity():
    return AuthenticatedIdentity(
        user_id="user-1",
        email=None,
        username="field.operator",
        organization_id="org-tap",
        organization_code="TAP",
        role="TAP_ENGINEER",
        permissions=ROLE_PERMISSIONS["TAP_ENGINEER"],
        data_scope_type=None,
        data_scope_value=None,
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


def _message_envelope(*, message_id="wamid.1", sender="15550000001", text="CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"):
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
                            "messages": [
                                {
                                    "from": sender,
                                    "id": message_id,
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
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
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(_identity())
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    )
    assert response.status_code == 200


def test_post_invalid_signature_rejected(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "wrong-secret")}
    )
    assert response.status_code == 403


def test_post_missing_signature_rejected(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(WEBHOOK_PATH, content=body)
    assert response.status_code == 403


def test_post_fails_closed_when_app_secret_not_configured():
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "any-secret")}
    )
    assert response.status_code == 403


# --- POST payload routing ------------------------------------------------


def test_post_inbound_message_reaches_existing_intake_path(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(_identity())
    outbound = FakeOutboundClient()
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(_message_envelope(message_id="wamid.inbound1")).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    )
    assert response.status_code == 200
    assert len(repo.rows) == 1
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    assert repo.rows[0]["detected_domain"] == "CONDITION_MONITORING"
    # READY_FOR_CONFIRMATION carries a reply (the confirmation preview) --
    # it must reach the outbound adapter unchanged from the intake
    # service's own text, not reconstructed.
    assert len(outbound.calls) == 1
    assert outbound.calls[0] == ("+15550000001", repo.rows[0]["reply_text"])


def test_post_needs_information_reply_is_sent_outbound(monkeypatch):
    # MWO-025F's own test text: no "hari ini"/"today" -> READING_DATE_
    # REQUIRED -> NEEDS_INFORMATION, with the intake engine's existing
    # follow-up question as the reply (never a new one authored here).
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(_identity())
    outbound = FakeOutboundClient()
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(
        _message_envelope(
            message_id="wamid.needsinfo1",
            text="CMON 211-P-13AR: ditemukan kebocoran mechanical seal.",
        )
    ).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    )
    assert response.status_code == 200
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"
    assert len(outbound.calls) == 1
    assert outbound.calls[0] == ("+15550000001", "Reading date belum ada. Gunakan hari ini?")


def test_post_unknown_sender_receives_the_existing_safe_reply_outbound(monkeypatch):
    # No identity registered for this sender -> UNKNOWN_SENDER. The intake
    # service already defines a safe reply for this case ("Nomor WhatsApp
    # belum terdaftar.") -- MWO-025G Phase 4 requires sending it precisely
    # because that existing safe response is defined, not withholding it.
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(identity=None)
    outbound = FakeOutboundClient()
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(_message_envelope(message_id="wamid.unknown1")).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    )
    assert response.status_code == 200
    assert repo.rows == []
    assert outbound.calls == [("+15550000001", "Nomor WhatsApp belum terdaftar.")]


def test_post_status_callback_causes_no_engineering_write(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(_identity())
    outbound = FakeOutboundClient()
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(_status_envelope()).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    )
    assert response.status_code == 200
    assert response.json()["results"] == [{"status": "STATUS_ACKNOWLEDGED"}]
    assert repo.rows == []
    assert outbound.calls == []


def test_post_duplicate_delivery_does_not_create_duplicate_pending_intake(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(_identity())
    outbound = FakeOutboundClient()
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(_message_envelope(message_id="wamid.dup1")).encode("utf-8")
    signature = {"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    first = client.post(WEBHOOK_PATH, content=body, headers=signature)
    second = client.post(WEBHOOK_PATH, content=body, headers=signature)
    assert first.status_code == 200
    assert second.status_code == 200
    assert len(repo.rows) == 1
    # MWO-025G Phase 5: a duplicate Meta delivery of the same
    # provider_message_id must not produce a duplicate WhatsApp reply.
    assert len(outbound.calls) == 1


def test_post_unknown_event_safely_handled(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(_identity())
    outbound = FakeOutboundClient()
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(_unknown_envelope()).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    )
    assert response.status_code == 200
    assert response.json()["results"] == [{"status": "UNKNOWN_EVENT_ACKNOWLEDGED"}]
    assert repo.rows == []
    assert outbound.calls == []


def test_post_invalid_signature_never_reaches_outbound(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    outbound = FakeOutboundClient()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(_message_envelope()).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "wrong-secret")}
    )
    assert response.status_code == 403
    assert outbound.calls == []


# --- outbound delivery safety --------------------------------------------


def test_outbound_provider_failure_does_not_break_webhook_ack(monkeypatch):
    # The HTTP acknowledgement to Meta must remain fast and deterministic
    # even if the outbound provider call raises -- MWO-025G Phase 4/6.
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(_identity())
    outbound = FakeOutboundClient(raises=True)
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(_message_envelope(message_id="wamid.outboundfail1")).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "test-app-secret")}
    )
    assert response.status_code == 200
    assert len(repo.rows) == 1
    assert len(outbound.calls) == 1


def test_no_raw_phone_or_secret_in_logs(monkeypatch, caplog):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    repo = FakeIntakeRepository(_identity())
    outbound = FakeOutboundClient()
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: outbound
    body = json.dumps(_message_envelope(message_id="wamid.privacy1")).encode("utf-8")
    with caplog.at_level("INFO"):
        response = client.post(
            WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": _sign(body, "test-app-secret")}
        )
    assert response.status_code == 200
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "15550000001" not in log_text
    assert "+15550000001" not in log_text
    assert "test-app-secret" not in log_text

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
        self.pumps = {
            "211-P-13AR": {"tag_number": "211-P-13AR", "area": "HOC"},
            "210-P-05AR": {"tag_number": "210-P-05AR", "area": "HOC"},
        }

    def get_pump(self, tag_number):
        pump = self.pumps.get(tag_number)
        return {"success": bool(pump), "data": pump}


class FakeIntakeRepository:
    def __init__(self, identities=None):
        # identities: dict[normalized_phone_number, AuthenticatedIdentity]
        self.identities = identities or {}
        self.rows = []
        self._seq = 0

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
        actionable = {"READY_FOR_CONFIRMATION", "NEEDS_INFORMATION", "CONFIRMED"}
        rows = [r for r in self.rows if r["sender_user_id"] == sender_user_id and r["state"] in actionable]
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
            "confirmation_id": f"WA-CONF-{self._seq:04d}",
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


def _wire(monkeypatch, repo, outbound=None, pump_gateway=None):
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: (pump_gateway or FakePumpGateway())
    app.dependency_overrides[get_whatsapp_outbound_client] = lambda: (outbound or FakeOutboundClient())
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
    assert outbound.calls[-1] == (SENDER_A, "Data sudah dikonfirmasi.")


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

    response = _post(_message_envelope(message_id="wamid.badcode_ya1", text="YA WA-CONF-doesnotexist00000000000000"))

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

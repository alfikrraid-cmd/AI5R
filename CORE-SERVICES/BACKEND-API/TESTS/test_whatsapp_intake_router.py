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
from API.whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier, process_inbound_message
from dependencies import get_current_user, get_pm_occurrence_repository, get_condition_monitoring_reading_repository, get_pump_gateway, get_whatsapp_intake_repository
from main import app

client = TestClient(app)


class FakePumpGateway:
    def __init__(self):
        self.pumps = {
            "211-P-13AR": {"tag_number": "211-P-13AR", "area": "HOC"},
            "211-P-13BR": {"tag_number": "211-P-13BR", "area": "HOC"},
            "110-P-9A": {"tag_number": "110-P-9A", "area": "HOC"},
        }

    def get_pump(self, tag_number):
        pump = self.pumps.get(tag_number)
        return {"success": bool(pump), "data": pump}


class FakeIntakeRepository:
    def __init__(self, identity=None):
        self.identity = identity
        self.rows = []
        self.transitions = []

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
        row = {
            "intake_id": f"wa-{len(self.rows) + 1}",
            # Matches the real shape exactly (migration 030's
            # confirmation_id DEFAULT: 'WA-CONF-' + 32 lowercase hex chars)
            # -- required now that _CONFIRMATION_CODE_PATTERN strictly
            # requires exactly 32 hex characters.
            "confirmation_id": f"WA-CONF-{len(self.rows) + 1:032x}",
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
                if confirmed_by:
                    row["confirmed_by"] = confirmed_by
                    row["confirmed_at"] = "2026-08-27T00:00:00Z"
                if validation_result is not None:
                    row["validation_result"] = validation_result
                if structured_payload is not None:
                    row["structured_payload"] = structured_payload
                if last_outbound_provider_message_id is not None:
                    row["last_outbound_provider_message_id"] = last_outbound_provider_message_id
                self.transitions.append((intake_id, state))
                return row
        raise AssertionError("missing intake")


class BombEngineeringRepository:
    def create_draft(self, **kwargs):
        raise AssertionError("024A must not create PM/CMON records")


def _identity(role="TAP_ENGINEER", user_id="user-1", *, scope_type=None, scope_value=None):
    return AuthenticatedIdentity(
        user_id=user_id,
        email=None,
        username="field.operator",
        organization_id="org-tap",
        organization_code="TAP",
        role=role,
        permissions=ROLE_PERMISSIONS[role],
        data_scope_type=scope_type,
        data_scope_value=scope_value,
    )


@pytest.fixture(autouse=True)
def clear_overrides(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setenv("AI5R_WHATSAPP_INGRESS_SECRET", "test-secret")
    yield
    app.dependency_overrides.clear()


def _request(text, *, message_id="wamid.1", sender="+15550000001"):
    return {
        "provider": "whatsapp_cloud",
        "provider_message_id": message_id,
        "sender_identifier": sender,
        "text": text,
        "received_at": "2026-08-27T01:02:03Z",
    }


def _call_service(repo, text, *, message_id="wamid.1", pump_gateway=None):
    return process_inbound_message(
        provider="whatsapp_cloud",
        provider_message_id=message_id,
        sender_identifier="+15550000001",
        text=text,
        received_at="2026-08-27T01:02:03Z",
        repository=repo,
        pump_gateway=pump_gateway or FakePumpGateway(),
    )


def test_valid_known_sender_creates_ready_cmon_pending_payload():
    repo = FakeIntakeRepository(_identity())
    result = _call_service(repo, "CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor")
    assert result.status == "READY_FOR_CONFIRMATION"
    assert result.intake["detected_domain"] == "CONDITION_MONITORING"
    assert result.intake["structured_payload"]["measurements"]["mechseal_temp_de"] == 78.0
    assert result.intake["structured_payload"]["measurements"]["mechanical_seal_leak_de"] is False
    assert "Confirm?" in result.reply


def test_unknown_sender_rejected_without_pending_write():
    repo = FakeIntakeRepository(_identity())
    result = process_inbound_message(
        provider="whatsapp_cloud",
        provider_message_id="wamid.2",
        sender_identifier="+15550000002",
        text="CM 211-P-13AR hari ini DE 78",
        repository=repo,
        pump_gateway=FakePumpGateway(),
    )
    assert result.status == "REJECTED"
    assert result.message == "UNKNOWN_SENDER"
    assert repo.rows == []


def test_inactive_or_missing_membership_rejected_without_pending_write():
    repo = FakeIntakeRepository(identity=None)
    result = _call_service(repo, "CM 211-P-13AR hari ini DE 78")
    assert result.status == "REJECTED"
    assert repo.rows == []


def test_valid_pm_intent_creates_pending_payload():
    repo = FakeIntakeRepository(_identity())
    result = _call_service(repo, "PM 211-P-13AR hari ini flushing line selesai")
    assert result.status == "READY_FOR_CONFIRMATION"
    assert result.intake["detected_domain"] == "PM"
    assert result.intake["structured_payload"]["activities"][0]["done"] is True


def test_unknown_pump_needs_information_and_no_engineering_write():
    repo = FakeIntakeRepository(_identity())
    result = _call_service(repo, "CM 211-P-99A hari ini DE 78")
    assert result.status == "NEEDS_INFORMATION"
    assert "UNKNOWN_PUMP" in result.intake["validation_result"]["errors"]


def test_sister_pump_identity_is_preserved_without_fuzzy_correction():
    repo = FakeIntakeRepository(_identity())
    result = _call_service(repo, "CM 211-P-13AR hari ini DE 78")
    assert result.status == "READY_FOR_CONFIRMATION"
    assert result.intake["structured_payload"]["asset_code"] == "211-P-13AR"
    assert result.intake["structured_payload"]["asset_code"] != "211-P-13BR"


def test_missing_required_data_needs_information():
    repo = FakeIntakeRepository(_identity())
    result = _call_service(repo, "CM 211-P-13AR")
    assert result.status == "NEEDS_INFORMATION"
    assert "READING_DATE_REQUIRED" in result.intake["validation_result"]["errors"]
    assert "MEASUREMENT_REQUIRED" in result.intake["validation_result"]["errors"]


def test_duplicate_webhook_delivery_returns_existing_pending():
    repo = FakeIntakeRepository(_identity())
    first = _call_service(repo, "CM 211-P-13AR hari ini DE 78", message_id="wamid.dup")
    second = _call_service(repo, "CM 211-P-13AR hari ini DE 78", message_id="wamid.dup")
    assert first.intake["intake_id"] == second.intake["intake_id"]
    assert second.message == "DUPLICATE_DELIVERY"
    assert len(repo.rows) == 1


def test_duplicate_confirmation_is_idempotent():
    # Production regression fix, semantic update: a plain, unlinked "YA"
    # no longer treats CONFIRMED rows as discovery candidates, so with
    # nothing else open, the repeat correctly falls to the existing
    # NO_PENDING_CONFIRMATION message rather than DUPLICATE_CONFIRMATION.
    # The core guarantee this test proves -- no second CONFIRMED
    # transition -- still holds regardless.
    repo = FakeIntakeRepository(_identity())
    _call_service(repo, "CM 211-P-13AR hari ini DE 78")
    confirmed = _call_service(repo, "YA", message_id="wamid.confirm1")
    repeated = _call_service(repo, "YA", message_id="wamid.confirm2")
    assert confirmed.status == "CONFIRMED"
    assert repeated.message == "NO_PENDING_CONFIRMATION"
    assert [state for _, state in repo.transitions].count("CONFIRMED") == 1

    # DUPLICATE_CONFIRMATION remains fully reachable and idempotent via an
    # explicit reference to the already-confirmed row (unaffected by this
    # fix -- find_pending_by_confirmation_id does not filter by state).
    code = confirmed.intake["confirmation_id"]
    repeated_explicit = _call_service(repo, f"YA {code}", message_id="wamid.confirm3")
    assert repeated_explicit.message == "DUPLICATE_CONFIRMATION"
    assert [state for _, state in repo.transitions].count("CONFIRMED") == 1


def test_correction_request_returns_to_needs_information():
    repo = FakeIntakeRepository(_identity())
    _call_service(repo, "CM 211-P-13AR hari ini DE 78")
    result = _call_service(repo, "UBAH", message_id="wamid.change")
    assert result.status == "NEEDS_INFORMATION"
    assert "CORRECTION_REQUESTED" in result.intake["validation_result"]["errors"]


def test_cancellation_stops_pending_intake():
    repo = FakeIntakeRepository(_identity())
    _call_service(repo, "CM 211-P-13AR hari ini DE 78")
    result = _call_service(repo, "BATAL", message_id="wamid.cancel")
    assert result.status == "CANCELLED"


def test_unsupported_intent_rejected_without_engineering_write():
    repo = FakeIntakeRepository(_identity())
    result = _call_service(repo, "WO 211-P-13AR broken")
    assert result.status == "REJECTED"
    assert result.intake["detected_domain"] == "UNSUPPORTED_INTENT"


def test_provider_authentication_failure(monkeypatch):
    repo = FakeIntakeRepository(_identity())
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    response = client.post("/api/ltsa/whatsapp/intake", json=_request("CM 211-P-13AR hari ini DE 78"))
    assert response.status_code == 401


def test_api_known_sender_does_not_call_pm_or_cmon_create_repositories():
    repo = FakeIntakeRepository(_identity())
    app.dependency_overrides[get_whatsapp_intake_repository] = lambda: repo
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_pm_occurrence_repository] = lambda: BombEngineeringRepository()
    app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: BombEngineeringRepository()
    response = client.post(
        "/api/ltsa/whatsapp/intake",
        headers={"X-AI5R-WhatsApp-Ingress-Secret": "test-secret"},
        json=_request("CM 211-P-13AR hari ini DE 78 NDE 81 tidak bocor"),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "READY_FOR_CONFIRMATION"


def test_n8n_workflow_has_no_direct_sql_or_postgres_node():
    workflow = Path(__file__).resolve().parents[2] / "RUNTIME" / "WORKFLOWS" / "WF-LTSA-WHATSAPP-INTAKE-024A.json"
    text = workflow.read_text(encoding="utf-8")
    assert "postgres" not in text.casefold()
    assert "INSERT INTO" not in text
    assert "/api/ltsa/whatsapp/intake" in text

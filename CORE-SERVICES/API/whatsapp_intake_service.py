from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .auth_service import AuthenticatedIdentity, resolve_area_scope
from .pump_area_scope import is_asset_in_scope

SUPPORTED_INTENTS = frozenset({"PM", "CONDITION_MONITORING"})
PENDING_STATES = frozenset(
    {"RECEIVED", "NEEDS_INFORMATION", "READY_FOR_CONFIRMATION", "CONFIRMED", "CANCELLED", "REJECTED", "EXPIRED"}
)

_TAG_PATTERN = re.compile(r"\b\d{3}-P-\d+(?:AR|BR|[A-Z])?\b", re.IGNORECASE)
_NUMBER_AFTER = r"\s*[:=]?\s*(-?\d+(?:\.\d+)?)"


class WhatsAppIntakeRepositoryProtocol(Protocol):
    def find_identity_by_sender_hash(self, sender_hash: str) -> AuthenticatedIdentity | None: ...
    def find_pending_by_delivery_key(self, provider: str, provider_message_id: str, sender_user_id: str) -> dict | None: ...
    def find_pending_by_confirmation_id(self, confirmation_id: str, sender_user_id: str) -> dict | None: ...
    def find_latest_actionable_pending(self, sender_user_id: str) -> dict | None: ...
    def create_pending(self, payload: dict[str, Any]) -> dict: ...
    def transition_pending(
        self,
        intake_id: str,
        *,
        state: str,
        confirmed_by: str | None = None,
        validation_result: dict[str, Any] | None = None,
    ) -> dict: ...


class PumpGatewayProtocol(Protocol):
    def get_pump(self, tag_number: str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class IntakeResult:
    status: str
    message: str
    intake: dict[str, Any] | None = None
    reply: str | None = None


def normalize_sender_identifier(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits or len(digits) < 8 or len(digits) > 15:
        raise ValueError("Invalid sender identifier")
    return f"+{digits}"


def hash_sender_identifier(normalized_sender: str) -> str:
    return hashlib.sha256(normalized_sender.encode("utf-8")).hexdigest()


def normalized_payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def process_inbound_message(
    *,
    provider: str,
    provider_message_id: str,
    sender_identifier: str,
    text: str,
    repository: WhatsAppIntakeRepositoryProtocol,
    pump_gateway: PumpGatewayProtocol,
    received_at: str | None = None,
    provider_payload: dict[str, Any] | None = None,
) -> IntakeResult:
    normalized_sender = normalize_sender_identifier(sender_identifier)
    sender_hash = hash_sender_identifier(normalized_sender)
    identity = repository.find_identity_by_sender_hash(sender_hash)
    if identity is None:
        return IntakeResult(status="REJECTED", message="UNKNOWN_SENDER", reply="Nomor WhatsApp belum terdaftar.")

    stripped = (text or "").strip()
    existing_action = _handle_existing_pending_action(stripped, repository, identity)
    if existing_action is not None:
        return existing_action

    detected_domain = _detect_intent(stripped)
    if detected_domain not in SUPPORTED_INTENTS:
        return _persist(
            repository,
            provider=provider,
            provider_message_id=provider_message_id,
            sender_user_id=identity.user_id,
            received_at=received_at,
            original_message=stripped,
            detected_domain="UNSUPPORTED_INTENT",
            structured_payload={},
            validation_result={"valid": False, "errors": ["UNSUPPORTED_INTENT"]},
            state="REJECTED",
            provider_payload=provider_payload,
            reply="Format belum didukung. Gunakan awalan PM atau CM.",
        )

    structured_payload = _extract_payload(detected_domain, stripped, received_at=received_at)
    validation = _validate_payload(detected_domain, structured_payload, identity, pump_gateway)
    state = "READY_FOR_CONFIRMATION" if validation["valid"] else "NEEDS_INFORMATION"
    reply = _build_preview(detected_domain, structured_payload) if validation["valid"] else _build_follow_up(validation)
    return _persist(
        repository,
        provider=provider,
        provider_message_id=provider_message_id,
        sender_user_id=identity.user_id,
        received_at=received_at,
        original_message=stripped,
        detected_domain=detected_domain,
        structured_payload=structured_payload,
        validation_result=validation,
        state=state,
        provider_payload=provider_payload,
        reply=reply,
    )


def _handle_existing_pending_action(
    text: str, repository: WhatsAppIntakeRepositoryProtocol, identity: AuthenticatedIdentity
) -> IntakeResult | None:
    action = text.strip().casefold()
    if action not in {"ya", "y", "confirm", "ubah", "batal", "cancel"}:
        return None

    pending = repository.find_latest_actionable_pending(identity.user_id)
    if pending is None:
        return IntakeResult(status="REJECTED", message="NO_PENDING_CONFIRMATION", reply="Tidak ada data yang menunggu konfirmasi.")

    if action in {"ya", "y", "confirm"}:
        if pending.get("state") == "CONFIRMED":
            return IntakeResult(status="CONFIRMED", message="DUPLICATE_CONFIRMATION", intake=pending, reply="Data sudah dikonfirmasi.")
        updated = repository.transition_pending(pending["intake_id"], state="CONFIRMED", confirmed_by=identity.user_id)
        return IntakeResult(status="CONFIRMED", message="CONFIRMED_NO_ENGINEERING_WRITE", intake=updated, reply="Terkonfirmasi sebagai draft intake. Belum dibuat record PM/CMON.")

    if action in {"ubah"}:
        updated = repository.transition_pending(
            pending["intake_id"],
            state="NEEDS_INFORMATION",
            validation_result={"valid": False, "errors": ["CORRECTION_REQUESTED"]},
        )
        return IntakeResult(status="NEEDS_INFORMATION", message="CORRECTION_REQUESTED", intake=updated, reply="Kirim nilai yang perlu diubah.")

    updated = repository.transition_pending(pending["intake_id"], state="CANCELLED")
    return IntakeResult(status="CANCELLED", message="CANCELLED", intake=updated, reply="Dibatalkan. Tidak ada record dibuat.")


def _persist(repository: WhatsAppIntakeRepositoryProtocol, **payload: Any) -> IntakeResult:
    payload["normalized_payload_hash"] = normalized_payload_hash(payload["structured_payload"])
    duplicate = repository.find_pending_by_delivery_key(
        payload["provider"], payload["provider_message_id"], payload["sender_user_id"]
    )
    if duplicate is not None:
        return IntakeResult(status=duplicate["state"], message="DUPLICATE_DELIVERY", intake=duplicate, reply=duplicate.get("reply_text"))
    saved = repository.create_pending(payload)
    return IntakeResult(status=saved["state"], message="PENDING_CREATED", intake=saved, reply=payload.get("reply"))


def _detect_intent(text: str) -> str:
    head = text.strip().split(maxsplit=1)[0].casefold() if text.strip() else ""
    if head == "pm":
        return "PM"
    if head in {"cm", "cmon", "condition"}:
        return "CONDITION_MONITORING"
    return "UNSUPPORTED_INTENT"


def _extract_payload(domain: str, text: str, *, received_at: str | None) -> dict[str, Any]:
    tag_match = _TAG_PATTERN.search(text)
    asset_code = tag_match.group(0).upper() if tag_match else None
    payload: dict[str, Any] = {"domain": domain, "asset_code": asset_code, "asset_type": "PUMP", "source": "WHATSAPP_ENTRY"}
    if "hari ini" in text.casefold() or "today" in text.casefold():
        payload["entry_date"] = _date_from_received_at(received_at)

    if domain == "CONDITION_MONITORING":
        measurements: dict[str, Any] = {}
        de = _extract_number(r"\bDE\b" + _NUMBER_AFTER, text)
        nde = _extract_number(r"\bNDE\b" + _NUMBER_AFTER, text)
        if de is not None:
            measurements["mechseal_temp_de"] = de
        if nde is not None:
            measurements["mechseal_temp_nde"] = nde
        lowered = text.casefold()
        if "tidak bocor" in lowered or "no leak" in lowered:
            measurements["mechanical_seal_leak_de"] = False
            measurements["mechanical_seal_leak_nde"] = False
        elif "bocor" in lowered or "leak" in lowered:
            measurements["mechanical_seal_leak_de"] = True
            measurements["mechanical_seal_leak_nde"] = True
        payload["condition_monitoring_schedule_code"] = _extract_code(r"\b(?:schedule|jadwal)\s+([A-Z0-9:-]+)", text)
        payload["reading_date"] = payload.get("entry_date")
        payload["measurements"] = measurements
        return payload

    payload["pm_schedule_code"] = _extract_code(r"\b(?:schedule|jadwal)\s+([A-Z0-9:-]+)", text)
    payload["occurrence_date"] = payload.get("entry_date")
    activity_text = re.sub(_TAG_PATTERN, "", text, count=1)
    activity_text = re.sub(r"^\s*PM\b", "", activity_text, flags=re.IGNORECASE).strip()
    done = bool(re.search(r"\b(selesai|done|complete|completed)\b", activity_text, re.IGNORECASE))
    if activity_text:
        payload["activities"] = [{"code": "WHATSAPP-FREE-TEXT", "description": activity_text, "side": None, "done": done}]
    return payload


def _validate_payload(
    domain: str, payload: dict[str, Any], identity: AuthenticatedIdentity, pump_gateway: PumpGatewayProtocol
) -> dict[str, Any]:
    errors: list[str] = []
    tag = payload.get("asset_code")
    if not tag:
        errors.append("PUMP_TAG_REQUIRED")
    else:
        response = pump_gateway.get_pump(tag)
        pump = response.get("data") if isinstance(response, dict) else None
        if not isinstance(pump, dict) or pump.get("tag_number") != tag:
            errors.append("UNKNOWN_PUMP")
        else:
            scope = resolve_area_scope(identity)
            if scope is not None and not is_asset_in_scope(tag, scope, pump_gateway):
                errors.append("PUMP_OUT_OF_SCOPE")

    if domain == "CONDITION_MONITORING":
        if not payload.get("reading_date"):
            errors.append("READING_DATE_REQUIRED")
        if not payload.get("measurements"):
            errors.append("MEASUREMENT_REQUIRED")
    elif domain == "PM":
        if not payload.get("occurrence_date"):
            errors.append("OCCURRENCE_DATE_REQUIRED")
        if not payload.get("activities"):
            errors.append("PM_ACTIVITY_REQUIRED")
    return {"valid": not errors, "errors": errors}


def _build_preview(domain: str, payload: dict[str, Any]) -> str:
    if domain == "CONDITION_MONITORING":
        measurements = payload.get("measurements") or {}
        lines = ["Condition Monitoring", f"Pump: {payload.get('asset_code')}", f"Date: {payload.get('reading_date')}"]
        if "mechseal_temp_de" in measurements:
            lines.append(f"Seal Temp DE: {measurements['mechseal_temp_de']} C")
        if "mechseal_temp_nde" in measurements:
            lines.append(f"Seal Temp NDE: {measurements['mechseal_temp_nde']} C")
        if measurements.get("mechanical_seal_leak_de") is False and measurements.get("mechanical_seal_leak_nde") is False:
            lines.append("Leak: No")
        elif measurements.get("mechanical_seal_leak_de") is True or measurements.get("mechanical_seal_leak_nde") is True:
            lines.append("Leak: Yes")
    else:
        lines = ["Preventive Maintenance", f"Pump: {payload.get('asset_code')}", f"Date: {payload.get('occurrence_date')}"]
        for activity in payload.get("activities") or []:
            lines.append(f"Activity: {activity.get('description')}")
    lines.extend(["", "Confirm?", "YA / UBAH / BATAL"])
    return "\n".join(lines)


def _build_follow_up(validation: dict[str, Any]) -> str:
    errors = validation.get("errors") or []
    if "UNKNOWN_PUMP" in errors or "PUMP_TAG_REQUIRED" in errors:
        return "Kode pump tidak ditemukan. Kirim tag pump yang tepat."
    if "READING_DATE_REQUIRED" in errors:
        return "Reading date belum ada. Gunakan hari ini?"
    if "OCCURRENCE_DATE_REQUIRED" in errors:
        return "Tanggal PM belum ada. Gunakan hari ini?"
    if "MEASUREMENT_REQUIRED" in errors:
        return "Measurement belum ada. Kirim nilai yang diukur."
    if "PUMP_OUT_OF_SCOPE" in errors:
        return "Pump di luar scope akun Anda."
    return "Data belum lengkap. Mohon lengkapi informasi."


def _extract_number(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def _extract_code(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _date_from_received_at(received_at: str | None) -> str:
    if received_at:
        return received_at[:10]
    return datetime.now(timezone.utc).date().isoformat()


__all__ = [
    "IntakeResult",
    "PENDING_STATES",
    "SUPPORTED_INTENTS",
    "hash_sender_identifier",
    "normalize_sender_identifier",
    "normalized_payload_hash",
    "process_inbound_message",
]

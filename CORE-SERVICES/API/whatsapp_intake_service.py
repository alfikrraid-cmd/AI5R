from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from .auth_service import AuthenticatedIdentity, resolve_area_scope
from .pump_area_scope import is_asset_in_scope

logger = logging.getLogger(__name__)


def _correlation_id(value: str | None) -> str | None:
    # MWO-025J2 Part G -- never log a raw user UUID (tightens MWO-025G's
    # original choice to log identity.user_id verbatim). A truncated hash
    # is stable enough to correlate related log lines for one user across
    # a conversation without being reversible to the raw id.
    if not value:
        return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


SUPPORTED_INTENTS = frozenset({"PM", "CONDITION_MONITORING"})
PENDING_STATES = frozenset(
    {"RECEIVED", "NEEDS_INFORMATION", "READY_FOR_CONFIRMATION", "CONFIRMED", "CANCELLED", "REJECTED", "EXPIRED"}
)

# Production regression fix -- OPEN_PENDING_STATES is the ONLY set that may
# ever answer "what is a genuinely unresolved candidate for a plain, unlinked
# 'YA'". CONFIRMED is deliberately excluded here: a confirmed row is a
# finished transaction, not something still awaiting a decision, so it must
# never appear in candidate discovery (find_actionable_pending_list) or
# trigger AMBIGUOUS_PENDING_SELECTION. This is the single source of truth
# for that query; whatsapp_intake_repository.py's find_actionable_pending_
# list() SQL and every FakeIntakeRepository's own Python implementation of
# the same method already filter on this exact same set (duplicated there
# since they're SQL/test doubles, not importers of this module) -- keep
# them in sync if this set ever changes.
#
# This is a SEPARATE concept from "may _confirm_pending() act on it": that
# guard (in _confirm_pending itself) checks CONFIRMED first, as a distinct
# idempotent-duplicate branch, before ever consulting this set -- so
# OPEN_PENDING_STATES correctly describes both "candidate for discovery"
# and "eligible to actually transition" without CONFIRMED needing to be a
# member of either. An explicitly referenced CONFIRMED row (via WA-CONF
# code or Meta context.id -- both exact-match lookups with no state
# filter at all) remains fully resolvable and idempotent regardless of
# this set; only the discovery/transition side is scoped by it.
OPEN_PENDING_STATES = frozenset({"READY_FOR_CONFIRMATION", "NEEDS_INFORMATION"})

# Documentation-only grouping of PENDING_STATES' remaining non-open values
# (CONFIRMED is terminal too, but has its own idempotent-lookup branch in
# _confirm_pending and is intentionally not folded into this set).
TERMINAL_STATES = frozenset({"CANCELLED", "REJECTED", "EXPIRED"})

_TAG_PATTERN = re.compile(r"\b\d{3}-P-\d+(?:AR|BR|[A-Z])?\b", re.IGNORECASE)
_NUMBER_AFTER = r"\s*[:=]?\s*(-?\d+(?:\.\d+)?)"

# MWO-025J2 -- LTSA's configured business timezone for "hari ini"/"today"
# resolution (both at original intake and at confirmation-time date
# assignment). Asia/Jakarta (WIB) has no DST, so a fixed UTC+7 offset is
# exact and needs no tzdata dependency.
_LTSA_BUSINESS_TIMEZONE = timezone(timedelta(hours=7))

_ACTION_WORDS = frozenset({"ya", "y", "confirm", "ubah", "batal", "cancel"})
_DATE_FIELD_BY_DOMAIN = {"CONDITION_MONITORING": "reading_date", "PM": "occurrence_date"}
_DATE_ERROR_BY_DOMAIN = {"CONDITION_MONITORING": "READING_DATE_REQUIRED", "PM": "OCCURRENCE_DATE_REQUIRED"}

# Confirmation integrity fix -- confirmation_id is generated as
# 'WA-CONF-' || a 32-hex-char UUID (migration 030), always this exact
# shape. Matches it anywhere in the trailing text after the action word,
# so a reply that echoes AI5R's own "- WA-CONF-xxxx: CONDITION_MONITORING
# 211-P-13AR" listing format (trailing colon + descriptive label) still
# extracts just the code, deterministically -- never the raw remainder
# text, which would only ever equal the stored confirmation_id by luck.
_CONFIRMATION_CODE_PATTERN = re.compile(r"(WA-CONF-[0-9A-Fa-f]+)")


class WhatsAppIntakeRepositoryProtocol(Protocol):
    def find_identity_by_sender_hash(self, sender_hash: str) -> AuthenticatedIdentity | None: ...
    def find_pending_by_delivery_key(self, provider: str, provider_message_id: str, sender_user_id: str) -> dict | None: ...
    def find_pending_by_confirmation_id(self, confirmation_id: str, sender_user_id: str) -> dict | None: ...
    def find_latest_actionable_pending(self, sender_user_id: str) -> dict | None: ...
    def find_actionable_pending_list(self, sender_user_id: str) -> list[dict]: ...
    def find_pending_by_outbound_message_id(self, provider_message_id: str, sender_user_id: str) -> dict | None: ...
    def create_pending(self, payload: dict[str, Any]) -> dict: ...
    def transition_pending(
        self,
        intake_id: str,
        *,
        state: str,
        confirmed_by: str | None = None,
        validation_result: dict[str, Any] | None = None,
        structured_payload: dict[str, Any] | None = None,
        last_outbound_provider_message_id: str | None = None,
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
    context_message_id: str | None = None,
) -> IntakeResult:
    result = _process_inbound_message(
        provider=provider,
        provider_message_id=provider_message_id,
        sender_identifier=sender_identifier,
        text=text,
        repository=repository,
        pump_gateway=pump_gateway,
        received_at=received_at,
        provider_payload=provider_payload,
        context_message_id=context_message_id,
    )
    _log_intake_result(result)
    return result


def _log_intake_result(result: IntakeResult) -> None:
    intake = result.intake or {}
    structured_payload = intake.get("structured_payload") or {}
    logger.info(
        "event=whatsapp_intake_result classification=%s pump_tag=%s validation_result=%s "
        "pending_state=%s result_code=%s",
        intake.get("detected_domain") or "UNKNOWN",
        structured_payload.get("asset_code"),
        intake.get("validation_result"),
        intake.get("state") or result.status,
        result.message,
    )


def _process_inbound_message(
    *,
    provider: str,
    provider_message_id: str,
    sender_identifier: str,
    text: str,
    repository: WhatsAppIntakeRepositoryProtocol,
    pump_gateway: PumpGatewayProtocol,
    received_at: str | None = None,
    provider_payload: dict[str, Any] | None = None,
    context_message_id: str | None = None,
) -> IntakeResult:
    normalized_sender = normalize_sender_identifier(sender_identifier)
    sender_hash = hash_sender_identifier(normalized_sender)
    identity = repository.find_identity_by_sender_hash(sender_hash)
    if identity is None:
        logger.info("event=whatsapp_identity_resolution resolution=UNKNOWN_SENDER")
        return IntakeResult(status="REJECTED", message="UNKNOWN_SENDER", reply="Nomor WhatsApp belum terdaftar.")
    logger.info(
        "event=whatsapp_identity_resolution resolution=RESOLVED user_id=%s org=%s role=%s",
        _correlation_id(identity.user_id),
        identity.organization_code,
        identity.role,
    )

    stripped = (text or "").strip()
    existing_action = _handle_existing_pending_action(
        stripped, repository, identity, pump_gateway, context_message_id
    )
    if existing_action is not None:
        return existing_action

    detected_domain = _detect_intent(stripped)
    if detected_domain not in SUPPORTED_INTENTS:
        return _persist(
            repository,
            provider=provider,
            provider_message_id=provider_message_id,
            sender_user_id=identity.user_id,
            organization_id=identity.organization_id,
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
        organization_id=identity.organization_id,
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
    text: str,
    repository: WhatsAppIntakeRepositoryProtocol,
    identity: AuthenticatedIdentity,
    pump_gateway: PumpGatewayProtocol,
    context_message_id: str | None,
) -> IntakeResult | None:
    tokens = text.strip().split(maxsplit=1)
    if not tokens:
        return None
    action = tokens[0].casefold()
    if action not in _ACTION_WORDS:
        return None
    remainder = tokens[1].strip() if len(tokens) > 1 else None
    # Only treat this as an explicit code selector when a WA-CONF-shaped
    # token actually appears in the remainder -- trailing text that never
    # contained a code (e.g. "YA please") falls through to the normal
    # single/ambiguous-pending resolution below instead of being rejected
    # as an unrecognized code.
    selector_match = _CONFIRMATION_CODE_PATTERN.search(remainder) if remainder else None
    selector = selector_match.group(1) if selector_match else None

    # MWO-025J2 Part E -- context-linked resolution takes priority: if this
    # reply is a Meta reply/quote of a specific AI5R outbound message, that
    # unambiguously identifies the pending conversation, regardless of what
    # else the user has pending.
    pending = None
    if context_message_id:
        pending = repository.find_pending_by_outbound_message_id(context_message_id, identity.user_id)

    # An explicit confirmation-code selector (e.g. "YA WA-CONF-AB12CD34")
    # also resolves directly -- this is the required clarification path
    # for an otherwise-ambiguous plain "YA" (see below).
    if pending is None and selector:
        pending = repository.find_pending_by_confirmation_id(selector, identity.user_id)
        if pending is None:
            return IntakeResult(status="REJECTED", message="UNKNOWN_CONFIRMATION_ID", reply="Kode konfirmasi tidak ditemukan.")

    if pending is None:
        candidates = repository.find_actionable_pending_list(identity.user_id)
        if not candidates:
            return IntakeResult(status="REJECTED", message="NO_PENDING_CONFIRMATION", reply="Tidak ada data yang menunggu konfirmasi.")
        if len(candidates) > 1:
            # MWO-025J2 Part E -- never guess which pending record a plain,
            # unlinked "YA" refers to when more than one is actionable.
            listing = "\n".join(
                f"- {candidate.get('confirmation_id')}: {candidate.get('detected_domain')} "
                f"{(candidate.get('structured_payload') or {}).get('asset_code')}"
                for candidate in candidates
            )
            return IntakeResult(
                status="NEEDS_INFORMATION",
                message="AMBIGUOUS_PENDING_SELECTION",
                reply=f"Ada beberapa data menunggu konfirmasi:\n{listing}\n\nBalas: YA <kode>",
            )
        pending = candidates[0]

    # MWO-025J2 Part D -- a pending row only belongs to the org context it
    # was created under. A generic "not found" reply (rather than a
    # distinct "wrong org" message) avoids disclosing cross-org existence
    # of another organization's pending data to a multi-org user currently
    # resolved into a different membership.
    pending_org = pending.get("organization_id")
    if pending_org is not None and pending_org != identity.organization_id:
        return IntakeResult(status="REJECTED", message="ORG_SCOPE_MISMATCH", reply="Data tidak ditemukan.")

    if action in {"ya", "y", "confirm"}:
        return _confirm_pending(pending, repository, identity, pump_gateway)

    if action == "ubah":
        updated = repository.transition_pending(
            pending["intake_id"],
            state="NEEDS_INFORMATION",
            validation_result={"valid": False, "errors": ["CORRECTION_REQUESTED"]},
        )
        return IntakeResult(status="NEEDS_INFORMATION", message="CORRECTION_REQUESTED", intake=updated, reply="Kirim nilai yang perlu diubah.")

    updated = repository.transition_pending(pending["intake_id"], state="CANCELLED")
    return IntakeResult(status="CANCELLED", message="CANCELLED", intake=updated, reply="Dibatalkan. Tidak ada record dibuat.")


def _confirm_pending(
    pending: dict[str, Any],
    repository: WhatsAppIntakeRepositoryProtocol,
    identity: AuthenticatedIdentity,
    pump_gateway: PumpGatewayProtocol,
) -> IntakeResult:
    if pending.get("state") == "CONFIRMED":
        # MWO-025J2 Part F -- idempotency: no re-transition, no re-stamped
        # confirmed_at, on any repeat "YA" for an already-confirmed row.
        return IntakeResult(status="CONFIRMED", message="DUPLICATE_CONFIRMATION", intake=pending, reply="Data sudah dikonfirmasi.")

    if pending.get("state") not in OPEN_PENDING_STATES:
        # State-guard fix -- a confirmation code is only ever actionable
        # from an open state (READY_FOR_CONFIRMATION/NEEDS_INFORMATION;
        # CONFIRMED already handled above). A terminal row -- EXPIRED (a
        # row superseded by bf8d525's own duplicate-intent fix included),
        # CANCELLED, or REJECTED -- must never be resurrected by replaying
        # its old code, however it was resolved (context link, explicit
        # WA-CONF selector, or plain "YA"): find_pending_by_confirmation_id
        # and find_pending_by_outbound_message_id do exact-match lookups
        # with no state filter at all, so this guard is the only thing
        # that stops a stale code from bypassing state validity. Reuses
        # the exact same rejection reply already used for a code that was
        # never issued at all -- never discloses that a stale/superseded
        # transaction once existed. No state change, no write.
        return IntakeResult(status="REJECTED", message="CONFIRMATION_NOT_ACTIONABLE", intake=pending, reply="Kode konfirmasi tidak ditemukan.")

    domain = pending.get("detected_domain")
    payload = dict(pending.get("structured_payload") or {})
    prior_errors = (pending.get("validation_result") or {}).get("errors") or []

    # MWO-025J2 Part A -- "YA" answering AI5R's own "Gunakan hari ini?"
    # question is interpreted as accepting today's date (LTSA business
    # timezone), but only when a date was actually the missing piece --
    # never invented for a field the user never spoke to.
    date_field = _DATE_FIELD_BY_DOMAIN.get(domain)
    date_error = _DATE_ERROR_BY_DOMAIN.get(domain)
    if date_field and date_error in prior_errors and not payload.get(date_field):
        today = _today_in_business_timezone()
        payload[date_field] = today
        payload.setdefault("entry_date", today)

    # MWO-025J2 Part C -- re-resolves authorization/area-scope using the
    # SAME canonical check _validate_payload already performs at original
    # intake (resolve_area_scope + is_asset_in_scope), against the
    # identity freshly resolved for THIS "YA" message -- not reused/cached
    # from the original message. No second permission model.
    validation = _validate_payload(domain, payload, identity, pump_gateway)

    if not validation["valid"]:
        # MWO-025J2 Part A -- CONFIRMED must mean valid. Still invalid
        # (whether the date fix wasn't enough, or scope changed) -> stay
        # NEEDS_INFORMATION and ask only for what's still missing/invalid.
        updated = repository.transition_pending(
            pending["intake_id"],
            state="NEEDS_INFORMATION",
            validation_result=validation,
            structured_payload=payload,
        )
        return IntakeResult(status="NEEDS_INFORMATION", message="STILL_INVALID", intake=updated, reply=_build_follow_up(validation))

    updated = repository.transition_pending(
        pending["intake_id"],
        state="CONFIRMED",
        confirmed_by=identity.user_id,
        validation_result=validation,
        structured_payload=payload,
    )
    return IntakeResult(
        status="CONFIRMED",
        message="CONFIRMED_NO_ENGINEERING_WRITE",
        intake=updated,
        reply="Terkonfirmasi sebagai draft intake. Belum dibuat record PM/CMON.",
    )


def _supersede_prior_actionable_same_intent(
    repository: WhatsAppIntakeRepositoryProtocol,
    sender_user_id: str,
    domain: str | None,
    asset_code: str | None,
) -> None:
    # Confirmation integrity fix -- a user resending essentially the same
    # CMON/PM request (e.g. impatient retries while waiting for AI5R's
    # missing-field question) arrives as genuinely distinct
    # provider_message_ids, so find_pending_by_delivery_key's redelivery
    # dedup never applies to it: each resend was, until now, creating its
    # own separate actionable pending row for the identical
    # (domain, asset_code) pair, which is exactly what produced multiple
    # simultaneous WA-CONF codes for one real-world intent. Expiring
    # prior still-open rows (NEEDS_INFORMATION/READY_FOR_CONFIRMATION --
    # never CONFIRMED; a completed confirmation is never touched by a
    # later message) for the same intent, only once this is confirmed to
    # be a genuinely new delivery (called from _persist after its own
    # duplicate check), keeps at most one actionable row per
    # (user, domain, asset_code) from this path.
    if not asset_code or not domain:
        return
    for row in repository.find_actionable_pending_list(sender_user_id):
        if row.get("state") not in {"NEEDS_INFORMATION", "READY_FOR_CONFIRMATION"}:
            continue
        if row.get("detected_domain") != domain:
            continue
        if (row.get("structured_payload") or {}).get("asset_code") != asset_code:
            continue
        repository.transition_pending(row["intake_id"], state="EXPIRED")


def _persist(repository: WhatsAppIntakeRepositoryProtocol, **payload: Any) -> IntakeResult:
    payload["normalized_payload_hash"] = normalized_payload_hash(payload["structured_payload"])
    duplicate = repository.find_pending_by_delivery_key(
        payload["provider"], payload["provider_message_id"], payload["sender_user_id"]
    )
    if duplicate is not None:
        return IntakeResult(status=duplicate["state"], message="DUPLICATE_DELIVERY", intake=duplicate, reply=duplicate.get("reply_text"))
    _supersede_prior_actionable_same_intent(
        repository,
        payload["sender_user_id"],
        payload.get("detected_domain"),
        (payload.get("structured_payload") or {}).get("asset_code"),
    )
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


def _today_in_business_timezone() -> str:
    return datetime.now(_LTSA_BUSINESS_TIMEZONE).date().isoformat()


def _date_from_received_at(received_at: str | None) -> str:
    if received_at:
        return received_at[:10]
    return _today_in_business_timezone()


__all__ = [
    "IntakeResult",
    "PENDING_STATES",
    "SUPPORTED_INTENTS",
    "hash_sender_identifier",
    "normalize_sender_identifier",
    "normalized_payload_hash",
    "process_inbound_message",
]

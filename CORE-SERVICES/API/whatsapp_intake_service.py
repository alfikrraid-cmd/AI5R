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


class ConditionMonitoringWriterProtocol(Protocol):
    # Authoritative CMON writer -- CORE-SERVICES/API/
    # condition_monitoring_reading_repository.py's ConditionMonitoringReadingRepository
    # already implements every method here; reused as-is, not duplicated.
    def find_by_source_reference(self, source_reference: str) -> dict | None: ...
    def find_open_schedules_by_asset(self, asset_code: str) -> list[dict]: ...
    def create_draft(
        self,
        *,
        condition_monitoring_schedule_code: str,
        asset_code: str,
        asset_type: str | None,
        reading_date: str | None,
        measurements: dict,
        created_by: str,
        provenance: str,
        source_reference: str | None,
        finding: str | None,
    ) -> dict: ...
    def create_ad_hoc_draft(
        self,
        *,
        asset_code: str,
        asset_type: str | None,
        reading_date: str | None,
        measurements: dict,
        created_by: str,
        source_reference: str,
        finding: str | None,
        provenance: str,
    ) -> dict | None: ...


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
    cmon_repository: ConditionMonitoringWriterProtocol | None = None,
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
        cmon_repository=cmon_repository,
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
    cmon_repository: ConditionMonitoringWriterProtocol | None = None,
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
        stripped, repository, identity, pump_gateway, context_message_id, cmon_repository
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
    cmon_repository: ConditionMonitoringWriterProtocol | None = None,
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

    # Production diagnostic instrumentation -- read-only tracking of which
    # resolution path this call actually took, so a report like "why did
    # this exact retry return NO_PENDING_CONFIRMATION" is answerable from
    # logs alone next time, without a manual DB reproduction. Every branch
    # below is byte-identical to before; only _emit() (which logs, then
    # returns its argument unchanged) was inserted at each existing return
    # site -- no new repository calls, no reordering, no changed values.
    explicit_lookup_attempted = False
    explicit_lookup_found = False
    explicit_lookup_state: str | None = None
    broad_lookup_attempted = False
    broad_candidate_count: int | None = None

    def _emit(result: IntakeResult) -> IntakeResult:
        logger.info(
            "event=whatsapp_confirmation_selection action=%s selector_present=%s selector_hash=%s "
            "identity_user_hash=%s explicit_lookup_attempted=%s explicit_lookup_found=%s "
            "explicit_lookup_state=%s broad_lookup_attempted=%s broad_candidate_count=%s result_code=%s",
            action,
            selector is not None,
            _correlation_id(selector),
            _correlation_id(identity.user_id),
            explicit_lookup_attempted,
            explicit_lookup_found,
            explicit_lookup_state,
            broad_lookup_attempted,
            broad_candidate_count,
            result.message,
        )
        return result

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
        explicit_lookup_attempted = True
        pending = repository.find_pending_by_confirmation_id(selector, identity.user_id)
        if pending is None:
            return _emit(IntakeResult(status="REJECTED", message="UNKNOWN_CONFIRMATION_ID", reply="Kode konfirmasi tidak ditemukan."))
        explicit_lookup_found = True
        explicit_lookup_state = pending.get("state")

    if pending is None:
        broad_lookup_attempted = True
        candidates = repository.find_actionable_pending_list(identity.user_id)
        broad_candidate_count = len(candidates)
        if not candidates:
            return _emit(IntakeResult(status="REJECTED", message="NO_PENDING_CONFIRMATION", reply="Tidak ada data yang menunggu konfirmasi."))
        if len(candidates) > 1:
            # MWO-025J2 Part E -- never guess which pending record a plain,
            # unlinked "YA" refers to when more than one is actionable.
            listing = "\n".join(
                f"- {candidate.get('confirmation_id')}: {candidate.get('detected_domain')} "
                f"{(candidate.get('structured_payload') or {}).get('asset_code')}"
                for candidate in candidates
            )
            return _emit(IntakeResult(
                status="NEEDS_INFORMATION",
                message="AMBIGUOUS_PENDING_SELECTION",
                reply=f"Ada beberapa data menunggu konfirmasi:\n{listing}\n\nBalas: YA <kode>",
            ))
        pending = candidates[0]

    # MWO-025J2 Part D -- a pending row only belongs to the org context it
    # was created under. A generic "not found" reply (rather than a
    # distinct "wrong org" message) avoids disclosing cross-org existence
    # of another organization's pending data to a multi-org user currently
    # resolved into a different membership.
    pending_org = pending.get("organization_id")
    if pending_org is not None and pending_org != identity.organization_id:
        return _emit(IntakeResult(status="REJECTED", message="ORG_SCOPE_MISMATCH", reply="Data tidak ditemukan."))

    if action in {"ya", "y", "confirm"}:
        return _emit(_confirm_pending(pending, repository, identity, pump_gateway, cmon_repository))

    if action == "ubah":
        updated = repository.transition_pending(
            pending["intake_id"],
            state="NEEDS_INFORMATION",
            validation_result={"valid": False, "errors": ["CORRECTION_REQUESTED"]},
        )
        return _emit(IntakeResult(status="NEEDS_INFORMATION", message="CORRECTION_REQUESTED", intake=updated, reply="Kirim nilai yang perlu diubah."))

    updated = repository.transition_pending(pending["intake_id"], state="CANCELLED")
    return _emit(IntakeResult(status="CANCELLED", message="CANCELLED", intake=updated, reply="Dibatalkan. Tidak ada record dibuat."))


def _confirm_pending(
    pending: dict[str, Any],
    repository: WhatsAppIntakeRepositoryProtocol,
    identity: AuthenticatedIdentity,
    pump_gateway: PumpGatewayProtocol,
    cmon_repository: ConditionMonitoringWriterProtocol | None = None,
) -> IntakeResult:
    if pending.get("state") == "CONFIRMED":
        # MWO-025J2 Part F -- idempotency: no re-transition, no re-stamped
        # confirmed_at, on any repeat "YA" for an already-confirmed row.
        # Production hardening -- a CONFIRMED CONDITION_MONITORING row has
        # a real canonical record to disclose (source_reference is the
        # same immutable WHATSAPP::<intake_id> key _confirm_condition_
        # monitoring already writes with), so an explicit-code retry can
        # tell the engineer exactly which record already exists instead of
        # a generic message. Read-only lookup -- never calls create_draft/
        # create_ad_hoc_draft again, never calls transition_pending, so
        # confirmed_at/confirmed_by and the canonical row count are both
        # untouched by construction. PM (no cmon_repository match) and any
        # CMON row whose canonical record isn't found (e.g. a pre-da59a18
        # CONFIRMED_NO_ENGINEERING_WRITE row) fall through to the original
        # generic reply unchanged.
        if pending.get("detected_domain") == "CONDITION_MONITORING" and cmon_repository is not None:
            existing = cmon_repository.find_by_source_reference(f"WHATSAPP::{pending['intake_id']}")
            if existing is not None:
                asset_code = existing.get("asset_code") or (pending.get("structured_payload") or {}).get("asset_code")
                return IntakeResult(
                    status="CONFIRMED",
                    message="DUPLICATE_CONFIRMATION_CMON_RECORDED",
                    intake=pending,
                    reply=(
                        f"Condition Monitoring {asset_code} sudah tersimpan sebelumnya.\n"
                        f"Kode: {existing.get('condition_monitoring_reading_code')}"
                    ),
                )
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

    # Authoritative CMON writer -- PM is deliberately untouched (PM_CHANGE=
    # ZERO): only CONDITION_MONITORING reaches the write path below, and
    # only when a writer was actually supplied (callers that don't pass
    # one -- none currently, but this keeps the public function backward
    # compatible -- get the exact prior no-write behavior).
    has_real_writer = domain == "CONDITION_MONITORING" and cmon_repository is not None

    if has_real_writer and pending.get("state") != "READY_FOR_CONFIRMATION":
        # State-machine boundary fix -- "Ya" answering AI5R's own missing-
        # information question (e.g. "Gunakan hari ini?") is NOT the same
        # action as final confirmation, even though both currently arrive
        # as the literal text "Ya". Before an authoritative writer
        # existed, collapsing the two into one step was harmless (the
        # only outcome was a draft acknowledgement); now that CONFIRMED
        # can trigger a real, irreversible canonical write, a row that
        # was NEEDS_INFORMATION when this message arrived must stop here
        # at READY_FOR_CONFIRMATION and show the user the actual preview
        # -- never write until a SEPARATE, explicit final "Ya" (or
        # equivalent code/context reference) arrives against an
        # already-READY_FOR_CONFIRMATION row. Scoped to has_real_writer
        # only: PM (no writer exists) and CMON-without-a-writer keep the
        # exact prior single-step behavior, since nothing irreversible
        # happens on either of those paths either way.
        updated = repository.transition_pending(
            pending["intake_id"],
            state="READY_FOR_CONFIRMATION",
            validation_result=validation,
            structured_payload=payload,
        )
        return IntakeResult(
            status="READY_FOR_CONFIRMATION",
            message="TRANSITIONED_TO_READY_FOR_CONFIRMATION",
            intake=updated,
            reply=_build_preview(domain, payload),
        )

    if has_real_writer:
        return _confirm_condition_monitoring(pending, payload, validation, repository, identity, cmon_repository)

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


def _extract_cmon_finding(original_message: str | None) -> str | None:
    # Cleans the free-text observation out of the raw inbound message the
    # same way the PM path already strips its own tag/intent prefix
    # (_extract_payload's activity_text derivation) -- reused pattern, not
    # a new one. "CMON 211-P-13AR: ditemukan kebocoran mechanical seal"
    # -> "ditemukan kebocoran mechanical seal".
    text = re.sub(_TAG_PATTERN, "", original_message or "", count=1)
    text = re.sub(r"^\s*(?:CMON|CM|CONDITION)\b", "", text, flags=re.IGNORECASE).strip()
    text = text.lstrip(":").strip()
    return text or None


def _cmon_success_reply(record: dict[str, Any]) -> str:
    lines = [f"Condition Monitoring {record.get('asset_code')} berhasil disimpan."]
    if record.get("reading_date"):
        # Presentation-only -- the real repository's reading_date column is
        # TIMESTAMP, so a real DB row's value arrives as an ISO datetime
        # string ("2026-08-29T00:00:00"); a date-only string (Fake
        # repositories, tests) is unaffected since its own first 10 chars
        # are already the full value. Never touches the stored value/type.
        lines.append(f"Tanggal: {str(record['reading_date'])[:10]}")
    if record.get("condition_monitoring_reading_code"):
        lines.append(f"Kode: {record['condition_monitoring_reading_code']}")
    return "\n".join(lines)


def _confirm_condition_monitoring(
    pending: dict[str, Any],
    payload: dict[str, Any],
    validation: dict[str, Any],
    repository: WhatsAppIntakeRepositoryProtocol,
    identity: AuthenticatedIdentity,
    cmon_repository: ConditionMonitoringWriterProtocol,
) -> IntakeResult:
    intake_id = pending["intake_id"]
    # Idempotency -- deterministic, durable, DB-backed identity key built
    # from the immutable intake_id (never in-memory state, a timestamp, or
    # message text). A repeat "YA", a duplicate webhook delivery reaching
    # this point, or a retry after a network failure between the CMON
    # insert and the CONFIRMED transition below, all recompute this exact
    # same value and find the already-written row on the next attempt.
    source_reference = f"WHATSAPP::{intake_id}"

    already_written = cmon_repository.find_by_source_reference(source_reference)
    if already_written is not None:
        updated = repository.transition_pending(
            intake_id,
            state="CONFIRMED",
            confirmed_by=identity.user_id,
            validation_result=validation,
            structured_payload=payload,
        )
        logger.info("event=whatsapp_cmon_write result=ALREADY_RECORDED intake_id=%s", _correlation_id(intake_id))
        return IntakeResult(
            status="CONFIRMED",
            message="CONFIRMED_CMON_ALREADY_RECORDED",
            intake=updated,
            reply=_cmon_success_reply(already_written),
        )

    asset_code = payload.get("asset_code")
    open_schedules = cmon_repository.find_open_schedules_by_asset(asset_code)

    if len(open_schedules) > 1:
        # Never guess which schedule this reading belongs to. Pending
        # stays open (state unchanged) -- no write, no false confirmation
        # -- until the user picks one. Human-readable choices only, never
        # a raw internal schedule code the engineer would have to already
        # know.
        listing = "\n".join(
            f"{i}. {schedule.get('frequency') or schedule.get('condition_monitoring_schedule_code')}"
            for i, schedule in enumerate(open_schedules, start=1)
        )
        logger.info(
            "event=whatsapp_cmon_write result=AMBIGUOUS_SCHEDULE intake_id=%s candidate_count=%s",
            _correlation_id(intake_id),
            len(open_schedules),
        )
        return IntakeResult(
            status="NEEDS_INFORMATION",
            message="AMBIGUOUS_SCHEDULE_SELECTION",
            intake=pending,
            reply=(
                f"Ditemukan lebih dari satu jadwal Condition Monitoring untuk {asset_code}:\n"
                f"{listing}\nPilih nomor jadwal yang sesuai."
            ),
        )

    measurements = payload.get("measurements") or {}
    finding = _extract_cmon_finding(pending.get("original_message"))

    write_exception_class: str | None = None
    write_exception_sqlstate: str | None = None
    write_exception_summary: str | None = None
    try:
        if len(open_schedules) == 1:
            created = cmon_repository.create_draft(
                condition_monitoring_schedule_code=open_schedules[0]["condition_monitoring_schedule_code"],
                asset_code=asset_code,
                asset_type=payload.get("asset_type"),
                reading_date=payload.get("reading_date"),
                measurements=measurements,
                created_by=identity.user_id,
                provenance="WHATSAPP",
                source_reference=source_reference,
                finding=finding,
            )
        else:
            # Zero open schedules -- legitimate ad-hoc Condition Monitoring
            # (established precedent: PRODUCTS/LTSA-BRAIN/INGESTION/
            # ltsa_hoc_pm_cm_upsert.py's build_unscheduled_reference()).
            # Deterministic, no timestamp/UUID in the sentinel itself --
            # only source_reference (already unique per intake_id) carries
            # per-message identity.
            created = cmon_repository.create_ad_hoc_draft(
                asset_code=asset_code,
                asset_type=payload.get("asset_type"),
                reading_date=payload.get("reading_date"),
                measurements=measurements,
                created_by=identity.user_id,
                source_reference=source_reference,
                finding=finding,
                provenance="WHATSAPP",
            )
    except Exception as exc:
        # Covers create_draft's own WHERE EXISTS-no-match IndexError (e.g.
        # a schedule was cancelled/completed by someone else between the
        # find_open_schedules_by_asset check above and this insert) and
        # any other write-layer failure alike -- never a false success.
        # Exception class/SQLSTATE/a bounded first-line summary are
        # captured for observability (see the FAILED log line below) --
        # this is diagnostic-only: it was the missing piece that made the
        # original production ordering bug's actual cause invisible.
        # Never the phone number, raw provider payload, or full user
        # message -- none of those are ever part of a DB driver exception
        # in the first place.
        created = None
        write_exception_class = type(exc).__name__
        write_exception_sqlstate = getattr(exc, "pgcode", None)
        first_line = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
        write_exception_summary = first_line[:200] or None

    if not created:
        logger.info(
            "event=whatsapp_cmon_write result=FAILED intake_id=%s exception_class=%s sqlstate=%s error_summary=%s",
            _correlation_id(intake_id),
            write_exception_class,
            write_exception_sqlstate,
            write_exception_summary,
        )
        return IntakeResult(
            status="NEEDS_INFORMATION",
            message="CMON_WRITE_FAILED",
            intake=pending,
            reply="Gagal menyimpan Condition Monitoring. Silakan coba lagi.",
        )

    updated = repository.transition_pending(
        intake_id,
        state="CONFIRMED",
        confirmed_by=identity.user_id,
        validation_result=validation,
        structured_payload=payload,
    )
    logger.info(
        "event=whatsapp_cmon_write result=SUCCESS intake_id=%s schedule=%s",
        _correlation_id(intake_id),
        "REAL" if len(open_schedules) == 1 else "UNSCHEDULED",
    )
    return IntakeResult(
        status="CONFIRMED",
        message="CONFIRMED_CMON_RECORDED",
        intake=updated,
        reply=_cmon_success_reply(created),
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

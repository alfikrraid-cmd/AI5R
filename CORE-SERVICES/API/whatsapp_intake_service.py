from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
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


# TEMPORARY -- WhatsApp explicit-confirmation-selector routing
# investigation. Zero-width codepoints deliberately kept separate from
# Python's own str.isspace() classification below: several (e.g. ZERO
# WIDTH SPACE U+200B) are Unicode category Cf (Format), not Zs (Space
# Separator), so they are NOT stripped by .strip() and would NOT show up
# under "whitespace_codepoints" -- exactly the class of invisible
# character that could silently break a regex match while looking
# visually identical to the intended text. Remove this block and its
# call site once the routing investigation this exists to answer is
# closed.
_ZERO_WIDTH_CODEPOINTS = frozenset({
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x2060,  # WORD JOINER
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / BOM
})


_PREFIX_INSPECT_LENGTH = 8  # len("WA-CONF-") -- the fixed public protocol
# marker only. The 32-hex identifier begins at position 8 and is never
# inspected or logged by this diagnostic.
_EXPECTED_PREFIX_CASEFOLD = "wa-conf-"


def _log_confirmation_remainder_diagnostic(remainder: str) -> None:
    # Structural metadata only -- never the remainder text itself, never
    # any letter or digit from a confirmation token, never the phone
    # number/message/provider payload. Codepoint fields report the SET of
    # distinct codepoint TYPES encountered (as hex), never their
    # positions or the surrounding text.
    whitespace_codepoints = sorted({ord(ch) for ch in remainder if ch.isspace()})
    dash_like_codepoints = sorted({
        ord(ch) for ch in remainder if ch == "-" or unicodedata.category(ch) == "Pd"
    })
    zero_width_codepoints = sorted({
        ord(ch) for ch in remainder if ord(ch) in _ZERO_WIDTH_CODEPOINTS
    })
    # Prefix-only extension -- bounded by construction to the first 8
    # characters (Python slicing never reads past the string's own
    # length, so this is safe even for a shorter-than-expected
    # remainder). Positions 8+ (the 32-hex identifier) are NEVER sliced,
    # indexed, or logged here.
    prefix = remainder[:_PREFIX_INSPECT_LENGTH]
    prefix_codepoints = [hex(ord(ch)) for ch in prefix]
    logger.info(
        "event=whatsapp_confirmation_remainder_diagnostic remainder_length=%s remainder_sha256=%s "
        "starts_with_expected_ascii_prefix=%s contains_ascii_wa_conf=%s nfkc_changes_input=%s "
        "whitespace_codepoints=%s dash_like_codepoints=%s zero_width_codepoints=%s "
        "prefix_length_inspected=%s prefix_codepoints=%s prefix_casefold_matches_expected=%s",
        len(remainder),
        hashlib.sha256(remainder.encode("utf-8")).hexdigest()[:12],
        remainder.startswith("WA-CONF-"),
        "WA-CONF" in remainder,
        unicodedata.normalize("NFKC", remainder) != remainder,
        [hex(cp) for cp in whitespace_codepoints],
        [hex(cp) for cp in dash_like_codepoints],
        [hex(cp) for cp in zero_width_codepoints],
        len(prefix),
        prefix_codepoints,
        prefix.casefold() == _EXPECTED_PREFIX_CASEFOLD,
    )


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

# MWO-LTSA-WHATSAPP-ID-TAG-NORMALIZE-001 -- broadened from the original
# hyphen-required _TAG_PATTERN to also match separator-free/space-separated/
# mixed-case human input ("211p13ar", "211 P 13 AR", "211P-13AR") while
# keeping the exact same "AREA digits - P - NUMBER digits - optional
# AR/BR/single-letter suffix" shape and \b-anchored boundaries -- a
# malformed string with no isolated "P" between two digit runs (e.g.
# "999p999xyz", whose trailing "xyz" is not a valid 1-2 char suffix and
# leaves no word boundary for the pattern to anchor on) still does not
# match at all, never partially. This is the ONE tag-shape pattern for
# WhatsApp; _normalize_pump_tag_match() below is the ONE reshaping step --
# every extraction call site in this module uses both, never a second,
# competing normalizer. Existence (does a pump with this exact canonical
# tag actually exist?) is deliberately NOT decided here -- that is still
# _validate_payload's/_handle_ltsa_ai_query's own existing pump_gateway
# check, unchanged, so normalization can never bypass authorization or
# fabricate an asset that isn't real.
_TAG_PATTERN = re.compile(
    r"\b(\d{3})[\s-]*[Pp][\s-]*(\d+)(?:[\s-]*(AR|BR|[A-Za-z]))?\b", re.IGNORECASE
)
_NUMBER_AFTER = r"\s*[:=]?\s*(-?\d+(?:\.\d+)?)"


def _normalize_pump_tag_match(match: "re.Match[str]") -> str:
    """Reshapes an already-matched _TAG_PATTERN span into the canonical
    LTSA spelling (AREA-P-NUMBER[SUFFIX], suffix upper-cased) -- pure
    spelling normalization, no registry lookup, no existence claim."""
    area, number, suffix = match.group(1), match.group(2), match.group(3)
    canonical = f"{area}-P-{number}"
    if suffix:
        canonical += suffix.upper()
    return canonical


def _normalize_pump_tag_text(text: str) -> str | None:
    """Finds the first tag-shaped substring in free text and returns its
    canonical spelling, or None if no tag-shaped substring exists. Never
    confirms the tag is a REAL registered pump -- callers that need that
    guarantee (extraction call sites in this module) still go through the
    existing pump_gateway.get_pump()-based checks downstream, unchanged."""
    match = _TAG_PATTERN.search(text or "")
    return _normalize_pump_tag_match(match) if match else None

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
#
# Case-insensitivity fix -- production evidence (structural diagnostic
# only, never plaintext) proved a real retry arrived as lowercase
# "wa-conf-<hex>"; the prefix literal must match regardless of casing.
# re.IGNORECASE also covers the hex class (redundant with [0-9A-Fa-f]
# but harmless). The hex group is a FIXED {32} count with a trailing
# negative lookahead so this can never accept a truncated prefix of a
# longer hex run (33+ chars) or a short one (31 or fewer) -- .search()
# only has one viable anchor point (immediately after the literal
# "WA-CONF-"), so a run of the wrong length simply fails to match at
# all rather than silently matching a wrong-length substring. Unicode
# lookalike dashes/letters are still rejected: IGNORECASE only affects
# ASCII letter case, never non-ASCII codepoints.
_CONFIRMATION_HEX_LENGTH = 32
_CONFIRMATION_CODE_PATTERN = re.compile(
    rf"WA-CONF-([0-9A-Fa-f]{{{_CONFIRMATION_HEX_LENGTH}}})(?![0-9A-Fa-f])",
    re.IGNORECASE,
)


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


class PMWriterProtocol(Protocol):
    # Authoritative WhatsApp PM writer -- CORE-SERVICES/API/
    # pm_occurrence_repository.py's PMOccurrenceRepository already
    # implements every method here (create_draft() repaired in 31ea99c,
    # find_by_source_reference/find_open_schedules_by_asset/
    # create_ad_hoc_draft added in 51667f9); reused as-is, not duplicated.
    def find_by_source_reference(self, source_reference: str) -> dict | None: ...
    def find_open_schedules_by_asset(self, asset_code: str) -> list[dict]: ...
    def create_draft(
        self,
        *,
        pm_schedule_code: str,
        asset_code: str,
        asset_type: str | None,
        occurrence_date: str | None,
        activities: list | None,
        remarks: str | None,
        created_by: str,
        provenance: str,
        source_reference: str | None,
    ) -> dict: ...
    def create_ad_hoc_draft(
        self,
        *,
        asset_code: str,
        asset_type: str | None,
        occurrence_date: str | None,
        activities: list | None,
        remarks: str | None,
        created_by: str,
        source_reference: str,
        provenance: str,
    ) -> dict | None: ...


@dataclass(frozen=True, slots=True)
class LTSAAIQueryDependencies:
    # MWO: PRODUCTION READINESS + WHATSAPP -> LTSA AI INTEGRATION AUDIT --
    # bundles the exact same canonical gateways/services/AI client
    # routers/copilot.py's own ask_copilot_endpoint already depends on
    # (dependencies.py's existing get_maintenance_history_gateway/
    # get_work_order_gateway/get_installation_gateway/
    # get_ltsa_knowledge_service/get_equipment_timeline_service/
    # get_condition_monitoring_reading_gateway/
    # get_installation_report_repository/
    # get_mechanical_seal_stock_repository/get_copilot_ai_client) -- one
    # object so process_inbound_message's signature gains a single new
    # optional parameter instead of nine (now eleven, closing the two
    # gaps this MWO's own Phase 1/Phase 2 name: tag-scoped Condition
    # Monitoring via condition_monitoring_reading_repository -- the same
    # canonical repository the WhatsApp CMON WRITE flow already persists
    # through, reused read-only via list_by_asset() -- and fleet
    # priority/reliability via fleet_executive_summary_service, the same
    # canonical service routers/fleet.py's own /api/ltsa/fleet/powerbi
    # endpoint already serves). No new gateway, no new AI client, no
    # duplicated business logic: WhatsApp calls the exact same
    # ask_copilot()/orchestrate_copilot() functions the dashboard's own
    # /api/ltsa/copilot/ask route calls.
    ai_client: Any
    maintenance_history_gateway: Any
    work_order_gateway: Any
    installation_gateway: Any
    ltsa_knowledge_service: Any
    equipment_timeline_service: Any
    condition_monitoring_reading_gateway: Any
    installation_report_repository: Any
    mechanical_seal_stock_repository: Any
    condition_monitoring_reading_repository: Any
    fleet_executive_summary_service: Any
    # MWO-LTSA-EQUIPMENT-360-001 -- the SAME canonical direct-DB
    # repositories the WhatsApp PM/CM WRITE flows and the dashboard's own
    # cm_report router already use, closing the "PM terakhir"/"CM
    # terakhir" LTSA AI read-query gap that previously fell through to
    # ask_copilot()'s own default-constructed n8n gateways instead.
    pm_occurrence_repository: Any
    cm_report_repository: Any


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
    pm_repository: PMWriterProtocol | None = None,
    ltsa_ai_query_deps: LTSAAIQueryDependencies | None = None,
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
        pm_repository=pm_repository,
        ltsa_ai_query_deps=ltsa_ai_query_deps,
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
    pm_repository: PMWriterProtocol | None = None,
    ltsa_ai_query_deps: LTSAAIQueryDependencies | None = None,
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
        stripped, repository, identity, pump_gateway, context_message_id, cmon_repository, pm_repository
    )
    if existing_action is not None:
        return existing_action

    detected_domain = _detect_intent(stripped)
    if detected_domain not in SUPPORTED_INTENTS:
        # LTSA AI query routing -- deterministic gate: only reached once
        # PM/CMON has already been ruled out above, so a transactional
        # command is never intercepted. Read-only; never persists a
        # pending row (see _handle_ltsa_ai_query's own comment) -- a
        # question a caller asks leaves no state for a later "Ya" to act
        # on, unlike PM/CMON's own two-step confirmation flow.
        query_result = _handle_ltsa_ai_query(stripped, identity, pump_gateway, ltsa_ai_query_deps)
        if query_result is not None:
            return query_result
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
    pm_repository: PMWriterProtocol | None = None,
) -> IntakeResult | None:
    tokens = text.strip().split(maxsplit=1)
    if not tokens:
        return None
    action = tokens[0].casefold()
    if action not in _ACTION_WORDS:
        return None
    remainder = tokens[1].strip() if len(tokens) > 1 else None
    if remainder:
        _log_confirmation_remainder_diagnostic(remainder)
    # Only treat this as an explicit code selector when a WA-CONF-shaped
    # token actually appears in the remainder -- trailing text that never
    # contained a code (e.g. "YA please") falls through to the normal
    # single/ambiguous-pending resolution below instead of being rejected
    # as an unrecognized code.
    selector_match = _CONFIRMATION_CODE_PATTERN.search(remainder) if remainder else None
    # Canonicalize to the exact stored shape (migration 030's
    # confirmation_id DEFAULT: uppercase "WA-CONF-" + lowercase hex)
    # regardless of what case the user typed either half in -- the
    # repository lookup below is an exact string match, not
    # case-insensitive, so this must normalize BEFORE that call.
    selector = f"WA-CONF-{selector_match.group(1).lower()}" if selector_match else None

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
        return _emit(_confirm_pending(pending, repository, identity, pump_gateway, cmon_repository, pm_repository))

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
    pm_repository: PMWriterProtocol | None = None,
) -> IntakeResult:
    if pending.get("state") == "CONFIRMED":
        # MWO-025J2 Part F -- idempotency: no re-transition, no re-stamped
        # confirmed_at, on any repeat "YA" for an already-confirmed row.
        # Production hardening -- a CONFIRMED CONDITION_MONITORING/PM row
        # has a real canonical record to disclose (source_reference is
        # the same immutable WHATSAPP::<intake_id> key _confirm_condition_
        # monitoring/_confirm_pm already write with), so an explicit-code
        # retry can tell the engineer exactly which record already exists
        # instead of a generic message. Read-only lookup -- never calls
        # create_draft/create_ad_hoc_draft again, never calls
        # transition_pending, so confirmed_at/confirmed_by and the
        # canonical row count are both untouched by construction. Any row
        # whose canonical record isn't found (e.g. a pre-writer
        # CONFIRMED_NO_ENGINEERING_WRITE row) falls through to the
        # original generic reply unchanged.
        retry_domain = pending.get("detected_domain")
        if retry_domain == "CONDITION_MONITORING" and cmon_repository is not None:
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
        elif retry_domain == "PM" and pm_repository is not None:
            existing = pm_repository.find_by_source_reference(f"WHATSAPP::{pending['intake_id']}")
            if existing is not None:
                asset_code = existing.get("asset_code") or (pending.get("structured_payload") or {}).get("asset_code")
                return IntakeResult(
                    status="CONFIRMED",
                    message="DUPLICATE_CONFIRMATION_PM_RECORDED",
                    intake=pending,
                    reply=(
                        f"PM {asset_code} sudah tersimpan sebelumnya.\n"
                        f"Kode: {existing.get('pm_occurrence_code')}"
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

    # Authoritative writer dispatch -- CONDITION_MONITORING and PM each
    # reach their own write path below only when the matching writer was
    # actually supplied (a caller that passes neither -- none currently,
    # but this keeps the public function backward compatible -- gets the
    # exact prior no-write behavior for both domains).
    has_real_writer = (domain == "CONDITION_MONITORING" and cmon_repository is not None) or (
        domain == "PM" and pm_repository is not None
    )

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
        # only: a domain with no writer supplied keeps the exact prior
        # single-step behavior, since nothing irreversible happens on
        # that path either way.
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
        if domain == "CONDITION_MONITORING":
            return _confirm_condition_monitoring(pending, payload, validation, repository, identity, cmon_repository)
        return _confirm_pm(pending, payload, validation, repository, identity, pm_repository)

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


def _pm_success_reply(record: dict[str, Any]) -> str:
    lines = [f"PM {record.get('asset_code')} berhasil disimpan."]
    if record.get("occurrence_date"):
        # Presentation-only, same reasoning as _cmon_success_reply's own
        # identical slice: the real repository's occurrence_date column
        # is TIMESTAMP, so a real DB row's value arrives as an ISO
        # datetime string; a date-only string (Fake repositories, tests)
        # is unaffected. Never touches the stored value/type.
        lines.append(f"Tanggal: {str(record['occurrence_date'])[:10]}")
    if record.get("pm_occurrence_code"):
        lines.append(f"Kode: {record['pm_occurrence_code']}")
    schedule_code = record.get("pm_schedule_code") or ""
    if schedule_code.startswith("UNSCHEDULED::"):
        lines.append("Jadwal: Ad-hoc (tidak terjadwal)")
    elif schedule_code:
        lines.append(f"Jadwal: {schedule_code}")
    return "\n".join(lines)


def _confirm_pm(
    pending: dict[str, Any],
    payload: dict[str, Any],
    validation: dict[str, Any],
    repository: WhatsAppIntakeRepositoryProtocol,
    identity: AuthenticatedIdentity,
    pm_repository: PMWriterProtocol,
) -> IntakeResult:
    # Mirrors _confirm_condition_monitoring's exact structure/guarantees,
    # adapted to PM's own schema and business semantics (51667f9's own
    # repository support) -- not a copy of CMON semantics, but the same
    # proven orchestration shape: idempotency check, schedule resolution,
    # ambiguity guard, write-failure safety, all before any state change.
    intake_id = pending["intake_id"]
    source_reference = f"WHATSAPP::{intake_id}"

    already_written = pm_repository.find_by_source_reference(source_reference)
    if already_written is not None:
        updated = repository.transition_pending(
            intake_id,
            state="CONFIRMED",
            confirmed_by=identity.user_id,
            validation_result=validation,
            structured_payload=payload,
        )
        logger.info("event=whatsapp_pm_write result=ALREADY_RECORDED intake_id=%s", _correlation_id(intake_id))
        return IntakeResult(
            status="CONFIRMED",
            message="CONFIRMED_PM_ALREADY_RECORDED",
            intake=updated,
            reply=_pm_success_reply(already_written),
        )

    asset_code = payload.get("asset_code")
    open_schedules = pm_repository.find_open_schedules_by_asset(asset_code)

    if len(open_schedules) > 1:
        # Never guess which schedule this occurrence belongs to. Pending
        # stays open (state unchanged) -- no write, no false confirmation
        # -- until the user picks one. Human-readable choices only, never
        # a raw internal schedule code the engineer would have to already
        # know.
        listing = "\n".join(
            f"{i}. {schedule.get('procedure') or schedule.get('pm_schedule_code')}"
            for i, schedule in enumerate(open_schedules, start=1)
        )
        logger.info(
            "event=whatsapp_pm_write result=AMBIGUOUS_SCHEDULE intake_id=%s candidate_count=%s",
            _correlation_id(intake_id),
            len(open_schedules),
        )
        return IntakeResult(
            status="NEEDS_INFORMATION",
            message="AMBIGUOUS_SCHEDULE_SELECTION",
            intake=pending,
            reply=(
                f"Ditemukan lebih dari satu jadwal PM untuk {asset_code}:\n"
                f"{listing}\nPilih nomor jadwal yang sesuai."
            ),
        )

    activities = payload.get("activities")

    write_exception_class: str | None = None
    write_exception_sqlstate: str | None = None
    write_exception_summary: str | None = None
    try:
        if len(open_schedules) == 1:
            created = pm_repository.create_draft(
                pm_schedule_code=open_schedules[0]["pm_schedule_code"],
                asset_code=asset_code,
                asset_type=payload.get("asset_type"),
                occurrence_date=payload.get("occurrence_date"),
                activities=activities,
                remarks=None,
                created_by=identity.user_id,
                provenance="WHATSAPP",
                source_reference=source_reference,
            )
        else:
            # Zero open schedules -- legitimate ad-hoc PM (51667f9's own
            # domain-evidenced UNSCHEDULED::<source> convention, already
            # shipped in production via the historical batch importer).
            created = pm_repository.create_ad_hoc_draft(
                asset_code=asset_code,
                asset_type=payload.get("asset_type"),
                occurrence_date=payload.get("occurrence_date"),
                activities=activities,
                remarks=None,
                created_by=identity.user_id,
                source_reference=source_reference,
                provenance="WHATSAPP",
            )
    except Exception as exc:
        # Same diagnostic-only privacy/safety standard as _confirm_
        # condition_monitoring's own identical except-block: exception
        # class/SQLSTATE/a bounded first-line summary only, never the
        # phone number, raw provider payload, or full user message.
        created = None
        write_exception_class = type(exc).__name__
        write_exception_sqlstate = getattr(exc, "pgcode", None)
        first_line = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
        write_exception_summary = first_line[:200] or None

    if not created:
        logger.info(
            "event=whatsapp_pm_write result=FAILED intake_id=%s exception_class=%s sqlstate=%s error_summary=%s",
            _correlation_id(intake_id),
            write_exception_class,
            write_exception_sqlstate,
            write_exception_summary,
        )
        return IntakeResult(
            status="NEEDS_INFORMATION",
            message="PM_WRITE_FAILED",
            intake=pending,
            reply="Gagal menyimpan PM. Silakan coba lagi.",
        )

    updated = repository.transition_pending(
        intake_id,
        state="CONFIRMED",
        confirmed_by=identity.user_id,
        validation_result=validation,
        structured_payload=payload,
    )
    logger.info(
        "event=whatsapp_pm_write result=SUCCESS intake_id=%s schedule=%s",
        _correlation_id(intake_id),
        "REAL" if len(open_schedules) == 1 else "UNSCHEDULED",
    )
    return IntakeResult(
        status="CONFIRMED",
        message="CONFIRMED_PM_RECORDED",
        intake=updated,
        reply=_pm_success_reply(created),
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


# A question about EXISTING data ("CMON terakhir <tag>?", "Kapan terakhir
# PM <tag>?") is never a new reading/activity submission -- these are the
# only markers that flip a PM/CM/CMON-headed message from the
# transactional write below to LTSA AI query routing instead (checked
# against the remainder of the text, never the head word itself, so a
# genuine finding/activity report containing none of these is completely
# unaffected).
_QUERY_MARKER_PATTERN = re.compile(r"\?|\bterakhir\b|\bapa\b|\bbagaimana\b|\bkapan\b", re.IGNORECASE)


def _detect_intent(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "UNSUPPORTED_INTENT"
    parts = stripped.split(maxsplit=1)
    head = parts[0].casefold()
    rest = parts[1] if len(parts) > 1 else ""
    if head in {"pm", "cm", "cmon", "condition"} and _QUERY_MARKER_PATTERN.search(rest):
        return "UNSUPPORTED_INTENT"
    if head == "pm":
        return "PM"
    if head in {"cm", "cmon", "condition"}:
        return "CONDITION_MONITORING"
    return "UNSUPPORTED_INTENT"


# --- WhatsApp -> LTSA AI query routing -----------------------------------
#
# Deterministic gate, not "route every message to an LLM": this is only
# ever reached AFTER _detect_intent above has already ruled out PM/CMON
# (SUPPORTED_INTENTS), so "PM ..."/"CM ..."/"CMON ..." commands are
# completely unaffected and never reach this function at all. Within this
# function, copilot_ask_service's own _detect_intent (a SEPARATE,
# pre-existing keyword classifier already proven by the dashboard) decides
# whether the remaining text is a recognized LTSA question; if it isn't,
# this returns None and the caller falls through to the existing
# "Format belum didukung" message, unchanged.


def _extract_ltsa_ai_query_tag(text: str) -> str | None:
    return _normalize_pump_tag_text(text)


def _format_ltsa_ai_reply(answer: Any) -> str:
    # Phase 9's grounded response contract: the tool/AI-produced answer
    # text is already the compact, WhatsApp-appropriate summary (every
    # handler in copilot_ask_service.py already writes short, direct
    # sentences, not a dashboard-sized report) -- this only appends a
    # source/kind footer so a WhatsApp reader can see whether a RECOMMEN-
    # DATION/INTERPRETATION was distinguished from a plain FACT, and never
    # silently drops the DATA_GAP-vs-evidence distinction the orchestrator
    # already enforces upstream.
    from .copilot_ask_service import DATA_GAP

    if answer.kind == DATA_GAP and not answer.evidence:
        return answer.answer
    return f"{answer.answer}\n\nSumber: Data kanonik LTSA ({answer.kind})"


def _handle_ltsa_ai_query(
    text: str,
    identity: AuthenticatedIdentity,
    pump_gateway: PumpGatewayProtocol,
    ltsa_ai_query_deps: "LTSAAIQueryDependencies | None",
) -> IntakeResult | None:
    if ltsa_ai_query_deps is None:
        return None

    # Deferred import -- keeps whatsapp_intake_service.py's own import
    # graph independent of the copilot module unless a query is actually
    # in flight (mirrors this file's existing deferred-import discipline
    # elsewhere, e.g. the sys.path insert at module load for _INGESTION_DIR
    # in the sibling repository modules).
    from .copilot_ask_service import _detect_intent as _detect_copilot_intent
    from .copilot_orchestrator import orchestrate_copilot

    if _detect_copilot_intent(text) is None:
        return None

    tag = _extract_ltsa_ai_query_tag(text)
    scope = resolve_area_scope(identity)

    if tag is not None:
        # Same "safe not-found" discipline routers/copilot.py's own
        # _require_tag_in_scope already establishes: an out-of-scope tag
        # and a nonexistent tag get the exact same generic reply, never a
        # distinct status that would leak which case it was. Checked
        # BEFORE orchestrate_copilot()/ask_copilot() ever read any data
        # for this tag -- Phase 7's "WhatsApp query access must respect
        # the same data scope" and "unauthorized/out-of-scope must not
        # receive sensitive LTSA data" both enforced here, not trusted to
        # the read-only tool handlers downstream.
        response = pump_gateway.get_pump(tag)
        pump = response.get("data") if isinstance(response, dict) else None
        known = isinstance(pump, dict) and pump.get("tag_number") == tag
        if not known or not is_asset_in_scope(tag, scope, pump_gateway):
            return IntakeResult(status="REJECTED", message="LTSA_AI_QUERY_OUT_OF_SCOPE", reply=f"Tag pompa {tag} tidak ditemukan.")

    # MWO-LTSA-WHATSAPP-ID-LANGUAGE-001 -- WhatsApp is the one channel that
    # requests Indonesian output from the SAME LTSA AI/copilot; the
    # dashboard's own routers/copilot.py never passes language, so it keeps
    # ask_copilot()/orchestrate_copilot()'s existing "en" default untouched.
    answer, _tools_used = orchestrate_copilot(
        text,
        tag,
        scope,
        ltsa_ai_query_deps.ai_client,
        pump_gateway=pump_gateway,
        maintenance_history_gateway=ltsa_ai_query_deps.maintenance_history_gateway,
        work_order_gateway=ltsa_ai_query_deps.work_order_gateway,
        installation_gateway=ltsa_ai_query_deps.installation_gateway,
        ltsa_knowledge_service=ltsa_ai_query_deps.ltsa_knowledge_service,
        equipment_timeline_service=ltsa_ai_query_deps.equipment_timeline_service,
        condition_monitoring_reading_gateway=ltsa_ai_query_deps.condition_monitoring_reading_gateway,
        installation_report_repository=ltsa_ai_query_deps.installation_report_repository,
        mechanical_seal_stock_repository=ltsa_ai_query_deps.mechanical_seal_stock_repository,
        condition_monitoring_reading_repository=ltsa_ai_query_deps.condition_monitoring_reading_repository,
        fleet_executive_summary_service=ltsa_ai_query_deps.fleet_executive_summary_service,
        pm_occurrence_repository=ltsa_ai_query_deps.pm_occurrence_repository,
        cm_report_repository=ltsa_ai_query_deps.cm_report_repository,
        language="id",
    )
    # READ-ONLY by construction: every function reachable from here
    # (ask_copilot/orchestrate_copilot/TOOL_HANDLERS) only ever calls
    # .get_*/.list_*/.build*-style read methods -- there is no
    # create_pending, no transition_pending, no repository write call
    # anywhere on this path. No pending row is created for a query either
    # (nothing here calls _persist) -- a question can never leave state
    # behind for a later "Ya" to act on.
    return IntakeResult(status="ANSWERED", message="LTSA_AI_QUERY_ANSWERED", reply=_format_ltsa_ai_reply(answer))


def _extract_payload(domain: str, text: str, *, received_at: str | None) -> dict[str, Any]:
    asset_code = _normalize_pump_tag_text(text)
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
    # Cosmetic fix -- a message shaped "PM <tag>: <activity>" left a
    # leading ":" attached after the tag/prefix strip above (rendered as
    # "Activity: : check strainer" in the preview). Same leading-colon
    # strip _extract_cmon_finding already performs for the identical
    # "CMON <tag>: <finding>" shape -- brings PM in line with that
    # existing convention rather than introducing a new one.
    activity_text = activity_text.lstrip(":").strip()
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
    # MWO-LTSA-WHATSAPP-ID-LANGUAGE-001 -- field labels translated to
    # Bahasa Indonesia (Phase 6's "confirmation prompts" requirement);
    # domain nouns that are already standard LTSA technical vocabulary
    # (Condition Monitoring, Preventive Maintenance, PM/CMON) are kept
    # unchanged, matching Phase 6's own "technical nouns may remain
    # technical" carve-out.
    if domain == "CONDITION_MONITORING":
        measurements = payload.get("measurements") or {}
        lines = ["Condition Monitoring", f"Pompa: {payload.get('asset_code')}", f"Tanggal: {payload.get('reading_date')}"]
        if "mechseal_temp_de" in measurements:
            lines.append(f"Suhu Seal DE: {measurements['mechseal_temp_de']} C")
        if "mechseal_temp_nde" in measurements:
            lines.append(f"Suhu Seal NDE: {measurements['mechseal_temp_nde']} C")
        if measurements.get("mechanical_seal_leak_de") is False and measurements.get("mechanical_seal_leak_nde") is False:
            lines.append("Bocor: Tidak")
        elif measurements.get("mechanical_seal_leak_de") is True or measurements.get("mechanical_seal_leak_nde") is True:
            lines.append("Bocor: Ya")
    else:
        lines = ["Preventive Maintenance", f"Pompa: {payload.get('asset_code')}", f"Tanggal: {payload.get('occurrence_date')}"]
        for activity in payload.get("activities") or []:
            lines.append(f"Aktivitas: {activity.get('description')}")
    lines.extend(["", "Konfirmasi?", "YA / UBAH / BATAL"])
    return "\n".join(lines)


def _build_follow_up(validation: dict[str, Any]) -> str:
    errors = validation.get("errors") or []
    if "UNKNOWN_PUMP" in errors or "PUMP_TAG_REQUIRED" in errors:
        return "Kode pompa tidak ditemukan. Kirim tag pompa yang tepat."
    if "READING_DATE_REQUIRED" in errors:
        return "Tanggal reading belum ada. Gunakan hari ini?"
    if "OCCURRENCE_DATE_REQUIRED" in errors:
        return "Tanggal PM belum ada. Gunakan hari ini?"
    if "MEASUREMENT_REQUIRED" in errors:
        return "Pengukuran belum ada. Kirim nilai yang diukur."
    if "PUMP_OUT_OF_SCOPE" in errors:
        return "Pompa di luar scope akun Anda."
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

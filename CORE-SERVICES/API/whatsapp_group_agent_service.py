"""
MWO-LTSA-TAP-GROUP-AGENT-001 -- TAP LTSA WhatsApp Group Agent: the
transport/security adapter that lets authorized TAP personnel inside
authorized WhatsApp groups ask LTSA/Equipment360 questions via
"/ltsa <question>". This module contains ZERO transport code (no Baileys,
no HTTP) and ZERO new LTSA reasoning -- it is a pure orchestration/gate
layer that calls the EXACT SAME orchestrate_copilot() function
routers/copilot.py's own /api/ltsa/copilot/ask endpoint already calls
(and the exact same tag-extraction helpers, imported not duplicated),
with the caller's *effective* scope (sender scope intersected with the
group's own optional scope) instead of a JWT-derived scope.

Deliberately does NOT reuse whatsapp_intake_service.process_inbound_message
-- that function has no parameter for a group-level scope constraint, and
this module must never modify that file. Deliberately DOES reuse
whatsapp_intake_service.normalize_sender_identifier/hash_sender_identifier
(identical phone-identity canonicalization, so a TAP member's registered
identity resolves the same way whether they message personally or from a
group) and the existing AuthenticatedIdentity/find_identity_by_sender_hash
lookup this whole codebase already uses everywhere else.

Security model (non-negotiable, enforced only here -- never in the LLM,
never in transport, never client-supplied):
  1. message must originate from a WhatsApp GROUP (transport's job to say so)
  2. group must exist in the allowlist and be ACTIVE
  3. message must start with the literal /ltsa trigger (first token, ci)
  4. sender must resolve to an existing, ACTIVE AI5R WhatsApp identity
  5. sender's own role/scope governs; group scope may only NARROW it
  6. response destination is ALWAYS event.group_id -- never derived from
     text, LLM output, quoted content, or anything else attacker-influenced
Every one of these is independently re-checked on every single message;
nothing is cached across messages in a way that could survive a
permission change (state is looked up fresh: identity ACTIVE-ness, group
ACTIVE-ness, rate-limit counters keyed by current time window).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .auth_service import AuthenticatedIdentity, resolve_area_scope
from .pump_area_scope import is_area_in_scope
from .whatsapp_group_media_store import (
    extract_pump_tag_candidates,
    format_file_size,
    normalize_pump_tag,
    sanitize_filename,
    validate_media_file,
)
from .whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier

logger = logging.getLogger(__name__)

_TRIGGER_RE = re.compile(r"^\s*/ltsa\b", re.IGNORECASE)
_USAGE_REPLY = "Silakan tulis pertanyaan setelah /ltsa.\nContoh: /ltsa status 212-P-8A"
_ACK_REPLY = "Tunggu sebentar ya..."
_UNAUTHORIZED_SENDER_REPLY = "Nomor Anda belum memiliki akses LTSA."
_UNAVAILABLE_REPLY = "LTSA sedang tidak tersedia. Silakan coba lagi nanti."
_RATE_LIMITED_REPLY = "Terlalu banyak permintaan. Silakan coba lagi sebentar lagi."


# --------------------------------------------------------------------------
# Inbound event shape -- transport-agnostic. The Baileys transport builds
# exactly this from a real WhatsApp event; tests build it directly. No
# field here is ever read as an authorization decision except through the
# functions in this module -- group_id and sender_identifier are kept as
# two always-distinct fields on purpose (mission requirement: "Never treat
# group ID as sender identity").
# --------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class GroupMessageEvent:
    group_id: str
    sender_identifier: str
    provider_message_id: str
    text: str
    is_from_self: bool = False
    is_group_message: bool = True
    timestamp: float | None = None
    media_type: str | None = None
    media_bytes_base64: str | None = None
    mimetype: str | None = None
    filename: str | None = None


@dataclass(frozen=True, slots=True)
class GroupAgentResult:
    status: str  # see _STATUS_* constants below
    reply: str | None = None
    ack: str | None = None


_STATUS_IGNORED_SELF = "IGNORED_SELF"
_STATUS_IGNORED_NOT_GROUP = "IGNORED_NOT_GROUP"
_STATUS_IGNORED_NO_TRIGGER = "IGNORED_NO_TRIGGER"
_STATUS_IGNORED_UNKNOWN_GROUP = "IGNORED_UNKNOWN_GROUP"
_STATUS_IGNORED_GROUP_NOT_ACTIVE = "IGNORED_GROUP_NOT_ACTIVE"
_STATUS_IGNORED_DUPLICATE = "IGNORED_DUPLICATE"
_STATUS_IGNORED_MALFORMED = "IGNORED_MALFORMED"
_STATUS_USAGE = "USAGE"
_STATUS_UNAUTHORIZED_SENDER = "UNAUTHORIZED_SENDER"
_STATUS_RATE_LIMITED = "RATE_LIMITED"
_STATUS_ANSWERED = "ANSWERED"
_STATUS_UNAVAILABLE = "UNAVAILABLE"
_STATUS_MEDIA_STAGED = "MEDIA_STAGED"
_STATUS_MEDIA_CONFIRMED = "MEDIA_CONFIRMED"
_STATUS_MEDIA_CANCELLED = "MEDIA_CANCELLED"
_STATUS_UNAUTHORIZED_MEDIA = "UNAUTHORIZED_MEDIA"
_STATUS_UNSUPPORTED_GENERIC_ATTACHMENT = "UNSUPPORTED_GENERIC_ATTACHMENT"
_STATUS_NO_PENDING_MEDIA = "NO_PENDING_MEDIA"
_STATUS_PARENT_RECORD_NOT_FOUND = "PARENT_RECORD_NOT_FOUND"
_STATUS_INVALID_MEDIA = "INVALID_MEDIA"
_STATUS_MALFORMED_MEDIA = "MALFORMED_MEDIA"
_STATUS_MISSING_PUMP_TAG = "MISSING_PUMP_TAG"
_STATUS_MULTIPLE_PUMP_TAGS = "MULTIPLE_PUMP_TAGS"
_STATUS_PUMP_NOT_FOUND = "PUMP_NOT_FOUND"
_STATUS_PUMP_OUT_OF_SCOPE = "PUMP_OUT_OF_SCOPE"


def hash_group_identifier(group_id: str) -> str:
    """Same construction as hash_sender_identifier -- a stable, one-way,
    non-reversible identifier safe to log/persist. No phone-shaped
    normalization applies to a group id (it is never a phone number), so
    this hashes the raw transport-supplied group id directly."""
    return hashlib.sha256((group_id or "").strip().encode("utf-8")).hexdigest()


def extract_ltsa_trigger(text: str) -> str | None:
    """Returns the question text (possibly empty string) if `text`'s first
    non-whitespace token is literally "/ltsa" (case-insensitive), else
    None. Deliberately NOT fuzzy: no @mention, no "tolong /ltsa", no
    substring match -- matches the mission's V1 trigger spec exactly."""
    if not text:
        return None
    match = _TRIGGER_RE.match(text)
    if not match:
        return None
    return text[match.end():].strip()


def intersect_scope(
    sender_scope: frozenset[str] | None, group_scope: frozenset[str] | None
) -> frozenset[str] | None:
    """None means "unrestricted" (matches resolve_area_scope's own
    convention throughout this codebase). Intersection, never union:
    - both unrestricted -> unrestricted
    - one restricted -> that restriction
    - both restricted -> the overlap (may be empty -- an empty frozenset
      is a real, valid "authorized for nothing" result, never silently
      upgraded to unrestricted)
    This is the ONLY scope-combination rule this module implements; scope
    itself is still computed by the existing resolve_area_scope()."""
    if sender_scope is None:
        return group_scope
    if group_scope is None:
        return sender_scope
    return sender_scope & group_scope


# --------------------------------------------------------------------------
# Group authorization -- a separate, explicit model. NOT the user database.
# Phase 1: in-memory only (see whatsapp_group_repository_inmemory.py). A
# production-backed implementation is a proposed, NOT-applied migration
# (see ENGINEERING/MWO/MWO-LTSA-TAP-GROUP-AGENT-001-Proposed-Migration.md).
# --------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class GroupAuthorizationRecord:
    group_hash: str
    display_label: str
    status: str  # "PENDING" | "ACTIVE" | "DISABLED"
    allowed_scope: frozenset[str] | None = None


class GroupNotFoundError(ValueError):
    """Shared across every GroupAuthorizationRepositoryProtocol
    implementation (in-memory, Postgres) -- callers (e.g. the admin
    lifecycle router) catch this one class regardless of which
    implementation is wired in, never a repository-specific subclass."""


class GroupAuthorizationRepositoryProtocol(Protocol):
    def find_group_by_hash(self, group_hash: str) -> GroupAuthorizationRecord | None: ...

    def record_seen_message(self, provider_message_id: str) -> bool:
        """Atomically record a provider_message_id as seen. Returns True
        the first time a given id is recorded, False on every subsequent
        call for the same id (i.e. this IS the dedupe/replay guard) --
        never returns True twice for the same id, regardless of call
        order or concurrency, per the implementation's own contract."""
        ...


class SenderIdentityRepositoryProtocol(Protocol):
    def find_identity_by_sender_hash(self, sender_hash: str) -> AuthenticatedIdentity | None: ...


class WhatsAppGroupMediaStoreProtocol(Protocol):
    def stage_media(
        self,
        *,
        sender_user_id: str,
        sender_hash: str,
        group_hash: str,
        raw_bytes: bytes,
        mimetype: str,
        filename: str,
        pump_tag: str,
        target_type: str,
        target_record_code: str,
        target_record_id: int | None = None,
        target_record_date: str | None = None,
        category: str = "OTHER",
    ) -> Any: ...

    def get_pending(self, sender_user_id: str, group_hash: str) -> Any | None: ...

    def discard_pending(self, sender_user_id: str, group_hash: str) -> Any | None: ...


class PMCMEvidenceRepositoryProtocol(Protocol):
    def create(
        self,
        *,
        record_type: str,
        record_code: str,
        file_name: str,
        content_type: str,
        file_bytes: bytes,
        category: str | None,
        source: str,
        uploaded_by: str,
    ) -> dict: ...


class ConditionMonitoringReadingRepositoryProtocol(Protocol):
    def list_by_asset(self, asset_code: str) -> list[dict]: ...


class PMOccurrenceRepositoryProtocol(Protocol):
    def list_by_asset(self, asset_code: str) -> list[dict]: ...


class PumpGatewayProtocol(Protocol):
    def get_pump(self, tag: str) -> dict: ...


# --------------------------------------------------------------------------
# Rate limiting -- conservative, configurable, in-memory sliding counters.
# A dedicated Protocol so a future shared/multi-process limiter (e.g.
# Redis-backed) can replace this without touching the pipeline below.
# --------------------------------------------------------------------------
class RateLimiterProtocol(Protocol):
    def allow(self, *, sender_hash: str, group_hash: str) -> bool: ...


@dataclass(slots=True)
class RateLimitConfig:
    per_sender_per_minute: int = 6
    per_group_per_minute: int = 20
    global_per_minute: int = 120


class InMemoryRateLimiter:
    """Fixed-window counters (window = the current whole minute, UTC epoch
    // 60). Conservative and simple on purpose for Phase 1 -- a sliding
    window is a strict improvement a later phase can swap in behind the
    same Protocol without any pipeline change. Not shared across
    processes; a multi-instance deployment needs a shared backend before
    this limiter is trustworthy at scale (documented limitation, not
    hidden)."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._sender_counts: dict[tuple[int, str], int] = {}
        self._group_counts: dict[tuple[int, str], int] = {}
        self._global_counts: dict[int, int] = {}

    def allow(self, *, sender_hash: str, group_hash: str) -> bool:
        window = int(time.time() // 60)
        sender_key = (window, sender_hash)
        group_key = (window, group_hash)

        sender_count = self._sender_counts.get(sender_key, 0)
        group_count = self._group_counts.get(group_key, 0)
        global_count = self._global_counts.get(window, 0)

        if sender_count >= self.config.per_sender_per_minute:
            return False
        if group_count >= self.config.per_group_per_minute:
            return False
        if global_count >= self.config.global_per_minute:
            return False

        self._sender_counts[sender_key] = sender_count + 1
        self._group_counts[group_key] = group_count + 1
        self._global_counts[window] = global_count + 1
        return True


# --------------------------------------------------------------------------
# The pipeline itself -- mirrors the mission's own flowchart exactly, one
# guard per step, fail-closed on anything malformed or uncertain.
# --------------------------------------------------------------------------
def process_group_message(
    event: GroupMessageEvent,
    *,
    group_repository: GroupAuthorizationRepositoryProtocol,
    sender_identity_repository: SenderIdentityRepositoryProtocol,
    rate_limiter: RateLimiterProtocol,
    ask_ltsa_question: Callable[[str, "frozenset[str] | None"], str],
    media_store: WhatsAppGroupMediaStoreProtocol | None = None,
    pm_cm_evidence_repository: PMCMEvidenceRepositoryProtocol | None = None,
    condition_monitoring_reading_repository: ConditionMonitoringReadingRepositoryProtocol | None = None,
    pm_occurrence_repository: PMOccurrenceRepositoryProtocol | None = None,
    pump_gateway: PumpGatewayProtocol | None = None,
) -> GroupAgentResult:
    """`ask_ltsa_question(question, effective_scope) -> answer_text` is the
    ONLY point where this module calls into LTSA reasoning -- the caller
    (the router) supplies a closure that wraps orchestrate_copilot() with
    the existing gateways/AI client, exactly as routers/copilot.py's own
    endpoint does. This keeps this module fully unit-testable without any
    AI client, gateway, or database."""
    if event.is_from_self:
        return GroupAgentResult(status=_STATUS_IGNORED_SELF)

    if not event.is_group_message:
        return GroupAgentResult(status=_STATUS_IGNORED_NOT_GROUP)

    if not event.group_id or not event.sender_identifier or not event.provider_message_id:
        # Fail closed: malformed/incomplete event, never guessed at.
        return GroupAgentResult(status=_STATUS_IGNORED_MALFORMED)

    question = extract_ltsa_trigger(event.text)
    if question is None:
        # No trigger: ordinary group chatter. Terminate here, before any
        # dedupe/group/sender lookup -- this is the cheap fast path the
        # mission requires ("must terminate before LLM/Equipment360/DB").
        return GroupAgentResult(status=_STATUS_IGNORED_NO_TRIGGER)

    # Dedupe/replay guard -- checked before any group/sender lookup so a
    # replayed trigger message can never cause a second answer OR a second
    # acknowledgement, matching "avoid duplicate acknowledgement on
    # retries/replayed messages."
    if not group_repository.record_seen_message(event.provider_message_id):
        return GroupAgentResult(status=_STATUS_IGNORED_DUPLICATE)

    group_hash = hash_group_identifier(event.group_id)
    group = group_repository.find_group_by_hash(group_hash)
    if group is None:
        return GroupAgentResult(status=_STATUS_IGNORED_UNKNOWN_GROUP)
    if group.status != "ACTIVE":
        # Covers both PENDING and DISABLED -- both are silently ignored,
        # identically, per the mission's own explicit rule.
        return GroupAgentResult(status=_STATUS_IGNORED_GROUP_NOT_ACTIVE)

    try:
        sender_normalized = normalize_sender_identifier(event.sender_identifier)
    except ValueError:
        return GroupAgentResult(status=_STATUS_IGNORED_MALFORMED)
    sender_hash = hash_sender_identifier(sender_normalized)
    # find_identity_by_sender_hash already filters to status='ACTIVE' at
    # the query level (the same repository contract whatsapp_intake_
    # service.py and whatsapp_registration_service.py both already rely
    # on -- AuthenticatedIdentity itself carries no separate status field
    # to re-check here, by design: "resolved at all" already means
    # ACTIVE). A None result covers both "no such registration" and "
    # registration exists but is not ACTIVE" -- deliberately
    # indistinguishable in the reply, below.
    identity = sender_identity_repository.find_identity_by_sender_hash(sender_hash)
    if identity is None:
        # Generic denial only -- never distinguishes "no such number" from
        # "number exists but inactive" in the reply text.
        return GroupAgentResult(status=_STATUS_UNAUTHORIZED_SENDER, reply=_UNAUTHORIZED_SENDER_REPLY)

    lower_q = question.strip().lower()

    # ----------------------------------------------------------------------
    # Flow A: /ltsa confirm -> commit pending media
    # ----------------------------------------------------------------------
    if lower_q == "confirm":
        if "maintenance.write" not in identity.permissions:
            return GroupAgentResult(
                status=_STATUS_UNAUTHORIZED_MEDIA,
                reply="Nomor Anda tidak memiliki izin untuk mengonfirmasi penyimpanan media (diperlukan izin maintenance.write).",
            )
        if not rate_limiter.allow(sender_hash=sender_hash, group_hash=group_hash):
            return GroupAgentResult(status=_STATUS_RATE_LIMITED, reply=_RATE_LIMITED_REPLY)
        if not media_store:
            return GroupAgentResult(status=_STATUS_UNAVAILABLE, reply=_UNAVAILABLE_REPLY)

        pending = media_store.get_pending(sender_user_id=identity.user_id, group_hash=group_hash)
        if not pending:
            return GroupAgentResult(
                status=_STATUS_NO_PENDING_MEDIA,
                reply="Tidak ada media yang sedang menunggu konfirmasi atau sesi telah kedaluwarsa (15 menit).",
            )
        if not pm_cm_evidence_repository:
            return GroupAgentResult(status=_STATUS_UNAVAILABLE, reply=_UNAVAILABLE_REPLY)

        file_bytes = pending.get_bytes()
        if not file_bytes:
            media_store.discard_pending(sender_user_id=identity.user_id, group_hash=group_hash)
            return GroupAgentResult(
                status=_STATUS_MALFORMED_MEDIA,
                reply="File sementara tidak ditemukan atau rusak. Silakan unggah kembali.",
            )

        try:
            pm_cm_evidence_repository.create(
                record_type=pending.target_type,
                record_code=pending.target_record_code,
                file_name=pending.filename,
                content_type=pending.mimetype,
                file_bytes=file_bytes,
                category=pending.category,
                source="WHATSAPP_GROUP",
                uploaded_by=identity.user_id,
            )
        except Exception:
            logger.exception("Failed to insert evidence into pm_cm_evidence")
            return GroupAgentResult(status=_STATUS_UNAVAILABLE, reply=_UNAVAILABLE_REPLY)

        media_store.discard_pending(sender_user_id=identity.user_id, group_hash=group_hash)
        target_label = (
            "Condition Monitoring"
            if pending.target_type == "CONDITION_MONITORING_READING"
            else "Preventive Maintenance"
        )
        reply_text = (
            f"Dokumen/media *{pending.filename}* berhasil disimpan dan dikaitkan ke catatan "
            f"{target_label} (`{pending.target_record_code}`) untuk pompa *{pending.pump_tag}*."
        )
        return GroupAgentResult(status=_STATUS_MEDIA_CONFIRMED, reply=reply_text)

    # ----------------------------------------------------------------------
    # Flow B: /ltsa cancel -> discard pending media
    # ----------------------------------------------------------------------
    if lower_q == "cancel":
        if "maintenance.write" not in identity.permissions:
            return GroupAgentResult(
                status=_STATUS_UNAUTHORIZED_MEDIA,
                reply="Nomor Anda tidak memiliki izin untuk membatalkan unggahan media (diperlukan izin maintenance.write).",
            )
        if not rate_limiter.allow(sender_hash=sender_hash, group_hash=group_hash):
            return GroupAgentResult(status=_STATUS_RATE_LIMITED, reply=_RATE_LIMITED_REPLY)
        if not media_store:
            return GroupAgentResult(status=_STATUS_UNAVAILABLE, reply=_UNAVAILABLE_REPLY)

        discarded = media_store.discard_pending(sender_user_id=identity.user_id, group_hash=group_hash)
        if discarded:
            return GroupAgentResult(
                status=_STATUS_MEDIA_CANCELLED,
                reply=f"Unggahan media untuk pompa *{discarded.pump_tag}* telah dibatalkan.",
            )
        return GroupAgentResult(
            status=_STATUS_NO_PENDING_MEDIA,
            reply="Tidak ada media yang sedang menunggu konfirmasi.",
        )

    # ----------------------------------------------------------------------
    # Flow C: Inbound media ingestion (image/document attached)
    # ----------------------------------------------------------------------
    if event.media_type is not None or event.media_bytes_base64 is not None:
        if "maintenance.write" not in identity.permissions:
            return GroupAgentResult(
                status=_STATUS_UNAUTHORIZED_MEDIA,
                reply="Nomor Anda tidak memiliki izin untuk mengunggah dokumen/bukti media (diperlukan izin maintenance.write).",
            )
        if not rate_limiter.allow(sender_hash=sender_hash, group_hash=group_hash):
            return GroupAgentResult(status=_STATUS_RATE_LIMITED, reply=_RATE_LIMITED_REPLY)

        if question == "":
            return GroupAgentResult(
                status=_STATUS_USAGE,
                reply="Silakan sertakan perintah dan tag pompa pada caption media.\nContoh:\n/ltsa cm 211-P-16B\n/ltsa pm 211-P-16B",
            )

        tokens = question.strip().split()
        subcmd = tokens[0].lower()
        if subcmd in ("cm", "cmon"):
            target_type = "CONDITION_MONITORING_READING"
            target_label = "Condition Monitoring"
        elif subcmd == "pm":
            target_type = "PM_OCCURRENCE"
            target_label = "Preventive Maintenance"
        elif subcmd in ("laporan", "foto", "doc", "document"):
            candidates = extract_pump_tag_candidates(question)
            tag_hint = f" ({candidates[0]})" if candidates else ""
            return GroupAgentResult(
                status=_STATUS_UNSUPPORTED_GENERIC_ATTACHMENT,
                reply=(
                    f"Lampiran media umum untuk pompa{tag_hint} belum didukung pada skema database saat ini tanpa relasi CM/PM.\n"
                    "Silakan kaitkan media dengan catatan CM atau PM:\n"
                    "• /ltsa cm [TAG]\n"
                    "• /ltsa pm [TAG]"
                ),
            )
        else:
            return GroupAgentResult(
                status=_STATUS_USAGE,
                reply=(
                    "Perintah media tidak dikenali. Silakan gunakan perintah:\n"
                    "• /ltsa cm [TAG] (untuk Condition Monitoring)\n"
                    "• /ltsa pm [TAG] (untuk Preventive Maintenance)"
                ),
            )

        candidates = extract_pump_tag_candidates(question)
        if not candidates:
            return GroupAgentResult(
                status=_STATUS_MISSING_PUMP_TAG,
                reply=f"Mohon sertakan tag pompa pada caption. Contoh: /ltsa {subcmd} 211-P-16B",
            )
        if len(candidates) > 1:
            return GroupAgentResult(
                status=_STATUS_MULTIPLE_PUMP_TAGS,
                reply="Saya menemukan beberapa tag pompa di caption. Sebutkan satu tag pompa saja dan kirim ulang.",
            )

        pump_tag = normalize_pump_tag(candidates[0]) or candidates[0]
        sender_scope = resolve_area_scope(identity)
        effective_scope = intersect_scope(sender_scope, group.allowed_scope)

        if pump_gateway:
            response = pump_gateway.get_pump(pump_tag)
            pump_data = response.get("data") if isinstance(response, dict) else None
            if not isinstance(pump_data, dict):
                return GroupAgentResult(
                    status=_STATUS_PUMP_NOT_FOUND,
                    reply=f"Tag pompa {pump_tag} tidak ditemukan.",
                )
            pump_area = pump_data.get("area")
            if not is_area_in_scope(pump_area, effective_scope):
                return GroupAgentResult(
                    status=_STATUS_PUMP_OUT_OF_SCOPE,
                    reply=f"Tag pompa {pump_tag} berada di luar area wewenang Anda.",
                )

        # Resolve parent record
        if target_type == "CONDITION_MONITORING_READING":
            if not condition_monitoring_reading_repository:
                return GroupAgentResult(status=_STATUS_UNAVAILABLE, reply=_UNAVAILABLE_REPLY)
            readings = condition_monitoring_reading_repository.list_by_asset(pump_tag)
            if not readings:
                return GroupAgentResult(
                    status=_STATUS_PARENT_RECORD_NOT_FOUND,
                    reply=f"Tidak ditemukan catatan Condition Monitoring aktif untuk pompa {pump_tag}. Bukti media tidak dapat dikaitkan tanpa catatan CM induk.",
                )
            target_record = readings[0]
            target_record_code = target_record.get("condition_monitoring_reading_code") or ""
            target_record_id = target_record.get("reading_id")
            target_record_date = target_record.get("reading_date") or target_record.get("created_at") or "-"
        else:
            if not pm_occurrence_repository:
                return GroupAgentResult(status=_STATUS_UNAVAILABLE, reply=_UNAVAILABLE_REPLY)
            occurrences = pm_occurrence_repository.list_by_asset(pump_tag)
            if not occurrences:
                return GroupAgentResult(
                    status=_STATUS_PARENT_RECORD_NOT_FOUND,
                    reply=f"Tidak ditemukan catatan Preventive Maintenance aktif untuk pompa {pump_tag}. Bukti media tidak dapat dikaitkan tanpa catatan PM induk.",
                )
            target_record = occurrences[0]
            target_record_code = target_record.get("pm_occurrence_code") or ""
            target_record_id = target_record.get("occurrence_id")
            target_record_date = target_record.get("occurrence_date") or target_record.get("created_at") or "-"

        if not event.media_bytes_base64:
            return GroupAgentResult(status=_STATUS_MALFORMED_MEDIA, reply="Data media tidak ditemukan dalam pesan.")
        try:
            media_bytes = base64.b64decode(event.media_bytes_base64)
        except Exception:
            return GroupAgentResult(status=_STATUS_MALFORMED_MEDIA, reply="Data media rusak atau gagal didekode.")

        is_valid, err_msg = validate_media_file(media_bytes, declared_mimetype=event.mimetype or "")
        if not is_valid:
            return GroupAgentResult(status=_STATUS_INVALID_MEDIA, reply=err_msg or "Validasi media gagal.")

        if event.media_type == "image":
            category = "PHOTO"
        elif event.media_type == "document" and (
            event.mimetype == "application/pdf" or (event.filename or "").lower().endswith(".pdf")
        ):
            category = "REPORT"
        else:
            category = "OTHER"

        safe_name = sanitize_filename(
            event.filename or f"{subcmd}_{pump_tag}",
            fallback_ext=".jpg" if category == "PHOTO" else ".pdf",
        )
        if not media_store:
            return GroupAgentResult(status=_STATUS_UNAVAILABLE, reply=_UNAVAILABLE_REPLY)

        pending_rec = media_store.stage_media(
            sender_user_id=identity.user_id,
            sender_hash=sender_hash,
            group_hash=group_hash,
            raw_bytes=media_bytes,
            mimetype=event.mimetype or "application/octet-stream",
            filename=safe_name,
            pump_tag=pump_tag,
            target_type=target_type,
            target_record_code=target_record_code,
            target_record_id=target_record_id,
            target_record_date=str(target_record_date),
            category=category,
        )

        preview_text = (
            f"*Preview Bukti Media:*\n"
            f"• *File:* {pending_rec.filename} ({format_file_size(len(media_bytes))})\n"
            f"• *Target:* {target_label} (`{target_record_code}`)\n"
            f"• *Tanggal Catatan:* {target_record_date}\n"
            f"• *Pompa:* {pump_tag}\n\n"
            f"Ketik:\n"
            f"*/ltsa confirm* -> untuk menyimpan ke catatan\n"
            f"*/ltsa cancel* -> untuk membatalkan\n"
            f"_(Berlaku selama 15 menit)_"
        )
        return GroupAgentResult(status=_STATUS_MEDIA_STAGED, reply=preview_text)

    # ----------------------------------------------------------------------
    # Flow D: Standard text query flow
    # ----------------------------------------------------------------------
    if question == "":
        return GroupAgentResult(status=_STATUS_USAGE, reply=_USAGE_REPLY)

    if not rate_limiter.allow(sender_hash=sender_hash, group_hash=group_hash):
        # Rate-limit failure only ever reaches this point for an otherwise
        # fully-authorized request, per the mission's own rule.
        return GroupAgentResult(status=_STATUS_RATE_LIMITED, reply=_RATE_LIMITED_REPLY)

    sender_scope = resolve_area_scope(identity)
    effective_scope = intersect_scope(sender_scope, group.allowed_scope)

    try:
        answer = ask_ltsa_question(question, effective_scope)
    except Exception:
        logger.info(
            "event=whatsapp_group_agent_result group_hash=%s status=UNAVAILABLE",
            group_hash[:12],
        )
        return GroupAgentResult(status=_STATUS_UNAVAILABLE, reply=_UNAVAILABLE_REPLY, ack=_ACK_REPLY)

    logger.info(
        "event=whatsapp_group_agent_result group_hash=%s sender_hash=%s status=ANSWERED",
        group_hash[:12],
        sender_hash[:12],
    )
    return GroupAgentResult(status=_STATUS_ANSWERED, reply=answer, ack=_ACK_REPLY)


__all__ = [
    "GroupMessageEvent",
    "GroupAgentResult",
    "GroupAuthorizationRecord",
    "GroupNotFoundError",
    "GroupAuthorizationRepositoryProtocol",
    "SenderIdentityRepositoryProtocol",
    "WhatsAppGroupMediaStoreProtocol",
    "PMCMEvidenceRepositoryProtocol",
    "ConditionMonitoringReadingRepositoryProtocol",
    "PMOccurrenceRepositoryProtocol",
    "PumpGatewayProtocol",
    "RateLimiterProtocol",
    "RateLimitConfig",
    "InMemoryRateLimiter",
    "hash_group_identifier",
    "extract_ltsa_trigger",
    "intersect_scope",
    "process_group_message",
]


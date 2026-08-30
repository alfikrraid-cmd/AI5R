"""MWO-AI5R-LTSA-COPILOT-001 -- LTSA Dashboard Copilot minimum vertical
slice. Deterministic, keyword-based intent dispatch over ALREADY-EXISTING
LTSA services (maintenance_intelligence_service, ltsa_knowledge_service,
equipment_timeline_service, installation_gateway, pump_area_scope) -- no
LLM, no new gateway/service/container/database/vector DB. Every handler is
a thin read + format over an existing, dependency-injected service call
(the exact same gateway-injection convention routers/pumps.py's own
sub-resource routes already use), never a fresh, ungated gateway
instance -- "reuse before create", the same discipline every other
CORE-SERVICES module in this repository follows.

IDENTITY SAFETY (Hard Rules, this MWO):
  - A tag is never invented, defaulted, or guessed from question text --
    the caller (router) supplies an already scope-checked `tag`, resolved
    from asset_context/workspace selection, never parsed out of free text.
  - "current seal" is answered ONLY via EquipmentTimelineService.
    build_current_seal(tag) -- the same authoritative per-tag source
    routers/pumps.py's own /knowledge endpoint already uses for
    `current_seal` -- never via LTSAKnowledge.seal (the broader
    *compatible* seals list) and never by reading any other tag's data.
    DE/NDE is a position recorded on whatever installation/reading record
    build_current_seal or get_pump_condition_monitoring_flag already
    surfaces -- this module adds no DE/NDE derivation of its own, so it
    cannot conflate a seal position with a separate pump identity.
  - Every handler below reads exactly the one `tag` it was given -- there
    is no code path here that reads from a second tag to answer a
    question about the first.

Server-side authorization/scope is NOT this module's concern: the router
(routers/copilot.py) resolves resolve_area_scope(current_user) and denies
an out-of-scope tag before ask_copilot() is ever called (same
"safe not-found" discipline as routers/pumps.py's own _guard_tag_in_scope).
The one exception is the global (tag-less) work-orders intent, which
IS scope-filtered here (via pump_area_scope.filter_records_by_asset_scope,
reused unmodified) since it has no single tag for the router to gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from . import maintenance_intelligence_service as mis
from .pump_area_scope import filter_records_by_asset_scope

FACT = "FACT"
INTERPRETATION = "INTERPRETATION"
RECOMMENDATION = "RECOMMENDATION"
DATA_GAP = "DATA_GAP"

# MWO-LTSA-WHATSAPP-ID-LANGUAGE-001 -- every user-facing message in this
# module is keyed EN/ID rather than hardcoded English, selected by the
# `language` parameter threaded through ask_copilot()/every handler below.
# Default remains "en" everywhere (byte-identical to pre-existing behavior
# for every caller that doesn't pass language) -- only routers/copilot.py's
# dashboard endpoint keeps this default; whatsapp_intake_service.py is the
# one caller that explicitly requests "id". No second AI/response layer:
# this only changes which STRING TEMPLATE a given fact/gap is rendered
# into, never the underlying data/evidence/kind decision.
_NO_INTENT_MESSAGE = {
    "en": (
        "I couldn't match that question to a supported topic. Try asking about "
        "pump status, pump history, installation, PM/CM, work orders, "
        "seal/compatibility, inventory/stock, drawing/document, or recommendation."
    ),
    "id": (
        "Pertanyaan tidak dikenali. Coba tanyakan status pompa, riwayat pompa, "
        "instalasi, PM/CM, work order, seal/kompatibilitas, stok, gambar/dokumen, "
        "atau rekomendasi."
    ),
}
_NO_ASSET_MESSAGE = {
    "en": (
        "This question needs a specific pump/asset. Select an asset, or ask a "
        "fleet-wide question such as \"active work orders\"."
    ),
    "id": (
        "Pertanyaan ini butuh pompa/aset tertentu. Pilih aset, atau ajukan "
        "pertanyaan seluruh fleet seperti \"work order aktif\"."
    ),
}
_NO_PER_ASSET_TOOL_MESSAGE = {
    "en": (
        "I don't yet have a per-asset answer for that topic. Try a fleet-wide "
        "question instead, or ask about pump status, pump history, PM/CM, work "
        "orders, seal/compatibility, inventory/stock, drawing/document, or "
        "recommendation."
    ),
    "id": (
        "Belum ada jawaban per-aset untuk topik itu. Coba ajukan pertanyaan "
        "seluruh fleet, atau tanyakan status pompa, riwayat pompa, PM/CM, work "
        "order, seal/kompatibilitas, stok, gambar/dokumen, atau rekomendasi."
    ),
}


@dataclass(frozen=True, slots=True)
class CopilotAnswer:
    answer: str
    kind: str
    evidence: tuple[dict[str, Any], ...]


def _evidence(source: str, reference: str, field: str, value: Any) -> dict[str, Any]:
    return {"source": source, "reference": reference, "field": field, "value": "N/A" if value is None else str(value)}


# Ordered, most-specific-first -- first match wins. `current seal` is
# checked before the generic `seal` intent so "seal terakhir apa?" /
# "what's the current seal?" routes to the identity-safe single-record
# lookup instead of the broader compatibility list. `condition_monitoring`
# (bocor/leak) is checked before `cm` (corrective maintenance/kerusakan/
# breakdown) so a leak-symptom question never gets misrouted to the
# reactive-repair CM Report path -- ADR-CONDITION-MONITORING-001's own
# "CM Is a Terminology Collision" finding, reused, not re-litigated.
# `inventory` (stock/stok) is checked before `seal_compat` so a
# seal-stock question ("stok seal T48MP berapa?") is never misrouted to
# the compatibility-list intent just because it also mentions "seal".
#
# MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017 -- GENERIC synonym
# coverage (Indonesian/English), never one hardcoded sentence: every
# addition below is a real, common wording variant of a domain this
# router already had a handler for (or, for `condition_monitoring`, a
# domain this MWO adds) -- semantic routing, not a literal-string match.
def _detect_intent(question: str) -> str | None:
    q = (question or "").lower()

    def has(*words: str) -> bool:
        return any(re.search(word, q) for word in words)

    is_current_or_latest = has("current", "terakhir", "latest", "terbaru", "most recent", "sekarang", r"\bnow\b")
    is_install_or_replace_wording = has(
        "install", "pasang", "dipasang", "pemasangan", "ganti", "diganti", "replace", "replacement"
    )

    if has(r"\bseal\b", r"\bsegel\b") and is_current_or_latest and not is_install_or_replace_wording:
        return "current_seal"
    if has("install", "pasang", "dipasang", "pemasangan") or (
        has(r"\bseal\b", r"\bsegel\b") and has("ganti", "diganti", "replace", "replacement")
    ):
        return "installation"
    if has("bocor", r"\bleak", r"\bcmon\b", "condition monitoring", "temuan"):
        return "condition_monitoring"
    if has(r"\bpm\b", "preventive"):
        return "pm"
    if has(r"\bcm\b", "corrective", "breakdown", "kerusakan", r"\brusak"):
        return "cm"
    if has("work order", "workorder", r"\bwo\b", "kerja"):
        return "work_orders"
    if has("stock", "stok", "inventory", "inventaris", "spare part", "sparepart", "suku cadang", "tersedia"):
        return "inventory"
    if has(r"\bseal\b", r"\bsegel\b", "compatib", "cocok"):
        return "seal_compat"
    if has("drawing", "gambar", "document", "dokumen"):
        return "drawing_document"
    if has("perhatian", "perhatikan", "paling kritis", r"\bkritis\b", "prioritas", "priority", "critical pump", "most critical", "needs attention"):
        return "fleet_priority"
    if has("recommend", "rekomendasi", "saran"):
        return "recommendation"
    if has("history", "riwayat", "histori"):
        return "pump_history"
    if has("status", "kondisi"):
        return "pump_status"
    return None


# Entity extraction for a seal code mentioned near "seal"/"segel" OR
# "stock"/"stok" -- MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A adds
# the stock/stok anchor: "berapa stock T6014DP?" names no "seal" word at
# all. re.search() tries each anchor left-to-right and only accepts a
# position whose very next token has a digit, so "stock mechanical seal
# T48MP" correctly skips the digit-less "mechanical" after "stock" and
# still matches at "seal T48MP". Requires at least one digit in the
# captured token so a following word like "terakhir"/"compatibility"/
# "cocok" (no digit) is never mistaken for a code ("kapan seal terakhir
# diganti?" must NOT extract "terakhir" as a seal code) -- every real
# seal_code in this codebase's own registry (e.g. "SC-001", "T48MP",
# "T6014DP") contains at least one digit. Case preserved exactly as
# written (seal codes are case-sensitive identifiers) -- never normalized
# or guessed, the same "never invent" discipline routers/copilot.py's own
# pump-tag extraction already establishes.
_SEAL_CODE_PATTERN = re.compile(r"(?:seal|segel|stock|stok)\s+([A-Za-z0-9-]*\d[A-Za-z0-9-]*)", re.IGNORECASE)


def _extract_seal_code(question: str) -> str | None:
    match = _SEAL_CODE_PATTERN.search(question or "")
    return match.group(1) if match else None


# MWO-LTSA-AI-COPILOT-FLEET-STOCK-V1-017B -- fleet-wide stock predicate,
# checked only when intent=inventory, tag is None, and no single seal code
# was extracted (i.e. a genuinely fleet-scoped question, not a "stock for
# seal X" lookup, which stays on the 017A path unchanged). Simple substring
# checks, same style as _detect_intent's own `has()` -- never a hardcoded
# whole sentence, and priority-ordered (UNKNOWN/LOWEST checked before the
# broader OUT_OF_STOCK list) so "unknown"/"paling sedikit" are never
# swallowed by a looser out-of-stock phrase.
_UNKNOWN_STOCK_WORDS = ("unknown", "tidak diketahui", "belum diketahui")
_LOWEST_STOCK_WORDS = ("paling sedikit", "paling rendah", "paling minim", "lowest", "least", "fewest")
_OUT_OF_STOCK_WORDS = (
    "kosong", "habis", "ga ada", "gak ada", "tidak ada", "out of stock", "no seal stock",
    "no stock", "zero", "tidak tersedia", "ga tersedia", "gak tersedia", "not available",
)


def _detect_fleet_stock_predicate(question: str) -> str:
    q = (question or "").lower()

    def has(*words: str) -> bool:
        return any(word in q for word in words)

    if has(*_UNKNOWN_STOCK_WORDS):
        return "UNKNOWN_STOCK"
    if has(*_LOWEST_STOCK_WORDS):
        return "LOWEST_STOCK"
    if has(*_OUT_OF_STOCK_WORDS):
        return "OUT_OF_STOCK"
    return "AVAILABLE_STOCK"


def ask_copilot(
    question: str,
    tag: str | None,
    scope: frozenset[str] | None,
    *,
    pump_gateway,
    maintenance_history_gateway,
    work_order_gateway,
    installation_gateway,
    ltsa_knowledge_service,
    equipment_timeline_service,
    condition_monitoring_reading_gateway,
    installation_report_repository,
    mechanical_seal_stock_repository,
    condition_monitoring_reading_repository,
    fleet_executive_summary_service,
    language: str = "en",
) -> CopilotAnswer:
    intent = _detect_intent(question)

    if intent is None:
        return CopilotAnswer(_NO_INTENT_MESSAGE[language], DATA_GAP, ())

    # Tag-optional intents (MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017
    # adds the three below, matching `work_orders`' own pre-existing
    # tag-optional pattern): a fleet-wide question has no single asset for
    # the router to have extracted a tag from, and must not be rejected as
    # "needs a specific pump/asset" just because none was found.
    if intent == "work_orders" and tag is None:
        return _handle_global_work_orders(
            scope, pump_gateway=pump_gateway, work_order_gateway=work_order_gateway, language=language
        )

    if intent == "installation" and tag is None:
        # MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A -- reads via
        # installation_report_repository (direct-DB, always working), NOT
        # the broken n8n-backed installation_gateway the tag-scoped
        # `installation` handler below still uses -- see
        # installation_report_repository.py's own header for the full
        # root-cause disclosure and why only THIS fleet-wide path was
        # repointed.
        return _handle_latest_installation_fleet(
            scope, installation_report_repository=installation_report_repository, pump_gateway=pump_gateway,
            language=language,
        )

    if intent == "condition_monitoring" and tag is None:
        return _handle_leak_frequency_fleet(
            scope, condition_monitoring_reading_gateway=condition_monitoring_reading_gateway, pump_gateway=pump_gateway,
            language=language,
        )

    if intent == "fleet_priority":
        # No per-tag variant exists (or would make sense) for a ranking
        # question -- always fleet-wide, unlike work_orders/installation/
        # condition_monitoring above which only take this branch when tag
        # is None.
        return _handle_fleet_priority(scope, fleet_executive_summary_service=fleet_executive_summary_service, language=language)

    if intent == "inventory" and tag is None:
        seal_code = _extract_seal_code(question)
        if seal_code is not None:
            # MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A -- Stock V1
            # (mechanical_seal_stock_repository) is the ONLY stock
            # authority Copilot reads from; legacy seal_stock is not
            # wired into this module at all anymore (removed, not just
            # unused), so it structurally cannot contribute a quantity.
            return _handle_stock_by_seal_code(
                seal_code, mechanical_seal_stock_repository=mechanical_seal_stock_repository, language=language
            )
        # MWO-LTSA-AI-COPILOT-FLEET-STOCK-V1-017B -- a fleet-wide stock
        # question (no seal code named either) must not be rejected as
        # "needs a specific pump/asset" -- it IS the question.
        return _handle_fleet_stock_status(
            question, scope, mechanical_seal_stock_repository=mechanical_seal_stock_repository, pump_gateway=pump_gateway,
            language=language,
        )

    if tag is None:
        return CopilotAnswer(_NO_ASSET_MESSAGE[language], DATA_GAP, ())

    handler = TOOL_HANDLERS.get(intent)
    if handler is None:
        # _detect_intent recognizes more intents (e.g. "condition_monitoring")
        # than TOOL_HANDLERS has per-asset tools for -- those intents only
        # have a fleet-wide handler above (guarded by `tag is None`), so a
        # tag-scoped question here would otherwise raise an unhandled
        # KeyError instead of a graceful DATA_GAP answer.
        return CopilotAnswer(_NO_PER_ASSET_TOOL_MESSAGE[language], DATA_GAP, ())
    return handler(
        tag,
        pump_gateway=pump_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        installation_gateway=installation_gateway,
        ltsa_knowledge_service=ltsa_knowledge_service,
        equipment_timeline_service=equipment_timeline_service,
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        installation_report_repository=installation_report_repository,
        mechanical_seal_stock_repository=mechanical_seal_stock_repository,
        condition_monitoring_reading_repository=condition_monitoring_reading_repository,
        language=language,
    )


def _handle_pump_status(tag: str, *, pump_gateway, language: str = "en", **_: Any) -> CopilotAnswer:
    result = mis.get_pump_status(tag, pump_gateway=pump_gateway)
    pump = result.get("data")
    if not result.get("success") or not pump:
        if language == "id":
            return CopilotAnswer(f"Tag pompa {tag} tidak ditemukan.", DATA_GAP, ())
        return CopilotAnswer(f"Pump {tag} was not found.", DATA_GAP, ())
    if language == "id":
        answer = (
            f"{pump.get('tag_number', tag)} ({pump.get('pump_type', 'tipe tidak diketahui')}) saat ini "
            f"{pump.get('status') or 'TIDAK DIKETAHUI'}, berlokasi di {pump.get('location') or 'lokasi tidak diketahui'} "
            f"di area {pump.get('area') or 'tidak diketahui'}."
        )
    else:
        answer = (
            f"{pump.get('tag_number', tag)} ({pump.get('pump_type', 'unknown type')}) is currently "
            f"{pump.get('status') or 'UNKNOWN'}, located at {pump.get('location') or 'an unknown location'} "
            f"in area {pump.get('area') or 'an unknown area'}."
        )
    evidence = (_evidence("PumpGateway", tag, "status", pump.get("status")),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_pump_history(tag: str, *, maintenance_history_gateway, language: str = "en", **_: Any) -> CopilotAnswer:
    result = mis.get_pump_history(tag, maintenance_history_gateway=maintenance_history_gateway)
    if not result.get("success"):
        if language == "id":
            return CopilotAnswer(f"Riwayat pemeliharaan untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Maintenance history for {tag} is currently unavailable.", DATA_GAP, ())
    records = result.get("records") or []
    if not records:
        if language == "id":
            return CopilotAnswer(f"Tidak ada riwayat pemeliharaan untuk pompa {tag}.", FACT, ())
        return CopilotAnswer(f"No maintenance history found for pump {tag}.", FACT, ())
    if language == "id":
        lines = [
            f"- {r.get('maintenance_record_code')}: {r.get('action_taken')} oleh {r.get('performed_by') or 'tidak diketahui'} pada {r.get('performed_at') or 'tanggal tidak diketahui'}"
            for r in records
        ]
        answer = f"Pompa {tag} memiliki {len(records)} catatan pemeliharaan:\n" + "\n".join(lines)
    else:
        lines = [
            f"- {r.get('maintenance_record_code')}: {r.get('action_taken')} by {r.get('performed_by') or 'unknown'} on {r.get('performed_at') or 'an unknown date'}"
            for r in records
        ]
        answer = f"Pump {tag} has {len(records)} maintenance record(s):\n" + "\n".join(lines)
    evidence = tuple(
        _evidence("MaintenanceHistory", r.get("maintenance_record_code") or tag, "action_taken", r.get("action_taken"))
        for r in records
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_work_orders(tag: str, *, work_order_gateway, language: str = "en", **_: Any) -> CopilotAnswer:
    result = mis.get_active_work_orders(tag, work_order_gateway=work_order_gateway)
    if not result.get("success"):
        if language == "id":
            return CopilotAnswer(f"Data work order untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Work order data for {tag} is currently unavailable.", DATA_GAP, ())
    work_orders = result.get("work_orders") or []
    if not work_orders:
        if language == "id":
            return CopilotAnswer(f"Tidak ada work order aktif untuk pompa {tag}.", FACT, ())
        return CopilotAnswer(f"No active work orders for pump {tag}.", FACT, ())
    if language == "id":
        lines = [f"- {wo.get('work_order_code')}: {wo.get('status') or 'OPEN'} (ditugaskan ke {wo.get('assigned_to') or 'belum ada'})" for wo in work_orders]
        answer = f"{len(work_orders)} work order aktif untuk pompa {tag}:\n" + "\n".join(lines)
    else:
        lines = [f"- {wo.get('work_order_code')}: {wo.get('status') or 'OPEN'} (assigned to {wo.get('assigned_to') or 'nobody'})" for wo in work_orders]
        answer = f"{len(work_orders)} active work order(s) for pump {tag}:\n" + "\n".join(lines)
    evidence = tuple(
        _evidence("WorkOrderGateway", wo.get("work_order_code") or tag, "status", wo.get("status"))
        for wo in work_orders
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_global_work_orders(
    scope: frozenset[str] | None, *, pump_gateway, work_order_gateway, language: str = "en"
) -> CopilotAnswer:
    result = mis.get_active_work_orders(work_order_gateway=work_order_gateway)
    if not result.get("success"):
        if language == "id":
            return CopilotAnswer("Data work order sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer("Work order data is currently unavailable.", DATA_GAP, ())

    work_orders = result.get("work_orders") or []
    if scope is not None:
        work_orders = filter_records_by_asset_scope(work_orders, scope, pump_gateway)

    if not work_orders:
        if language == "id":
            return CopilotAnswer("Tidak ada work order aktif dalam cakupan otorisasi Anda.", FACT, ())
        return CopilotAnswer("No active work orders in your authorized scope.", FACT, ())

    if language == "id":
        lines = [f"- {wo.get('work_order_code')}: {wo.get('status') or 'OPEN'} ({wo.get('asset_code') or 'N/A'})" for wo in work_orders]
        answer = f"{len(work_orders)} work order aktif dalam cakupan otorisasi Anda:\n" + "\n".join(lines)
    else:
        lines = [f"- {wo.get('work_order_code')}: {wo.get('status') or 'OPEN'} ({wo.get('asset_code') or 'N/A'})" for wo in work_orders]
        answer = f"{len(work_orders)} active work order(s) in your authorized scope:\n" + "\n".join(lines)
    evidence = tuple(
        _evidence("WorkOrderGateway", wo.get("work_order_code") or "N/A", "status", wo.get("status")) for wo in work_orders
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_pm(tag: str, *, language: str = "en", **_: Any) -> CopilotAnswer:
    result = mis.get_pump_last_pm(tag)
    if not result.get("success"):
        if language == "id":
            return CopilotAnswer(f"Riwayat PM untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"PM history for {tag} is currently unavailable.", DATA_GAP, ())
    last_pm = result.get("last_pm")
    if not last_pm:
        if language == "id":
            return CopilotAnswer(f"Tidak ada catatan Preventive Maintenance (PM) untuk {tag}.", FACT, ())
        return CopilotAnswer(f"No preventive maintenance (PM) record found for {tag}.", FACT, ())
    if language == "id":
        answer = f"PM terakhir {tag} pada {last_pm.get('performed_at') or 'tanggal tidak diketahui'} (sumber: {last_pm.get('source') or 'N/A'})."
    else:
        answer = f"{tag}'s last PM was on {last_pm.get('performed_at') or 'an unknown date'} (source: {last_pm.get('source') or 'N/A'})."
    evidence = (_evidence("PMHistory", tag, "performed_at", last_pm.get("performed_at")),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_cm(tag: str, *, language: str = "en", **_: Any) -> CopilotAnswer:
    result = mis.get_pump_last_cm(tag)
    if not result.get("success"):
        if language == "id":
            return CopilotAnswer(f"Riwayat CM untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"CM history for {tag} is currently unavailable.", DATA_GAP, ())
    last_cm = result.get("last_cm")
    if not last_cm:
        if language == "id":
            return CopilotAnswer(f"Tidak ada catatan Corrective Maintenance (CM) untuk {tag}.", FACT, ())
        return CopilotAnswer(f"No corrective maintenance (CM) record found for {tag}.", FACT, ())
    if language == "id":
        answer = (
            f"CM report terakhir {tag} adalah {last_cm.get('cm_report_code') or 'N/A'}, "
            f"severity {last_cm.get('severity') or 'N/A'}, status {last_cm.get('status') or 'N/A'}."
        )
    else:
        answer = (
            f"{tag}'s last CM report is {last_cm.get('cm_report_code') or 'N/A'}, "
            f"severity {last_cm.get('severity') or 'N/A'}, status {last_cm.get('status') or 'N/A'}."
        )
    evidence = (_evidence("CMReport", last_cm.get("cm_report_code") or tag, "severity", last_cm.get("severity")),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_current_seal(tag: str, *, equipment_timeline_service, language: str = "en", **_: Any) -> CopilotAnswer:
    try:
        current_seal = equipment_timeline_service.build_current_seal(tag)
        if current_seal is None:
            # Absence of an installation record is NOT proof of "no seal" --
            # never fabricated as a fact (Hard Rule: "Current seal must come
            # from evidence/history").
            if language == "id":
                return CopilotAnswer(f"Belum ada catatan instalasi seal terkini yang terkonfirmasi untuk {tag}.", DATA_GAP, ())
            return CopilotAnswer(f"No confirmed current-seal installation record exists for {tag}.", DATA_GAP, ())
        if language == "id":
            answer = (
                f"Seal terkini {tag} adalah {current_seal.seal_code or 'N/A'}"
                f"{f' ({current_seal.seal_name})' if current_seal.seal_name else ''}, "
                f"dipasang {current_seal.installed_at or 'tanggal tidak diketahui'} "
                f"(sumber: {current_seal.source})."
            )
        else:
            answer = (
                f"{tag}'s current seal is {current_seal.seal_code or 'N/A'}"
                f"{f' ({current_seal.seal_name})' if current_seal.seal_name else ''}, "
                f"installed {current_seal.installed_at or 'on an unknown date'} "
                f"(source: {current_seal.source})."
            )
        evidence = (_evidence(current_seal.source, current_seal.installation_code or tag, "seal_code", current_seal.seal_code),)
        return CopilotAnswer(answer, FACT, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Data seal terkini untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Current seal data for {tag} is currently unavailable.", DATA_GAP, ())


def _handle_seal_compat(tag: str, *, ltsa_knowledge_service, language: str = "en", **_: Any) -> CopilotAnswer:
    # Everything downstream of build() is inside this try -- a mis-shaped
    # result (e.g. a plain dict instead of an LTSAKnowledge object, from a
    # genuine service failure) must degrade to DATA_GAP, never propagate
    # as an unhandled 500 to the WhatsApp caller.
    try:
        knowledge = ltsa_knowledge_service.build(tag)
        seals = knowledge.seal or []
        if not seals:
            if language == "id":
                return CopilotAnswer(f"Tidak ada mechanical seal kompatibel yang terdaftar untuk {tag}.", FACT, ())
            return CopilotAnswer(f"No compatible mechanical seals are registered for {tag}.", FACT, ())
        lines = [f"- {s.get('seal_code')}: {s.get('part_name') or 'N/A'}" for s in seals]
        if language == "id":
            answer = f"{len(seals)} seal kompatibel untuk {tag}:\n" + "\n".join(lines)
        else:
            answer = f"{len(seals)} compatible seal(s) for {tag}:\n" + "\n".join(lines)
        evidence = tuple(_evidence("SealPumpCompatibility", s.get("seal_code") or tag, "part_name", s.get("part_name")) for s in seals)
        return CopilotAnswer(answer, FACT, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Data seal kompatibel untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Compatible seal data for {tag} is currently unavailable.", DATA_GAP, ())


def _handle_inventory(tag: str, *, ltsa_knowledge_service, language: str = "en", **_: Any) -> CopilotAnswer:
    try:
        knowledge = ltsa_knowledge_service.build(tag)
        inventory = knowledge.inventory or []
        if not inventory:
            if language == "id":
                return CopilotAnswer(f"Tidak ada catatan stok suku cadang untuk seal kompatibel {tag}.", FACT, ())
            return CopilotAnswer(f"No spare-part stock records are registered for {tag}'s compatible seals.", FACT, ())
        if language == "id":
            lines = [f"- {i.get('seal_code')}: qty tersedia {i.get('quantity_on_hand') if i.get('quantity_on_hand') is not None else 'N/A'} ({i.get('location') or 'N/A'})" for i in inventory]
            answer = f"Stok suku cadang untuk {tag}:\n" + "\n".join(lines)
        else:
            lines = [f"- {i.get('seal_code')}: qty on hand {i.get('quantity_on_hand') if i.get('quantity_on_hand') is not None else 'N/A'} ({i.get('location') or 'N/A'})" for i in inventory]
            answer = f"Spare-part stock for {tag}:\n" + "\n".join(lines)
        evidence = tuple(_evidence("MechanicalSealStockV1", i.get("stock_pool_id") or tag, "quantity_on_hand", i.get("quantity_on_hand")) for i in inventory)
        return CopilotAnswer(answer, FACT, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Data stok suku cadang untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Spare-part stock data for {tag} is currently unavailable.", DATA_GAP, ())


def _handle_drawing_document(tag: str, *, ltsa_knowledge_service, language: str = "en", **_: Any) -> CopilotAnswer:
    try:
        knowledge = ltsa_knowledge_service.build(tag)
        drawings = knowledge.drawings or []
        if not drawings:
            if language == "id":
                return CopilotAnswer(f"Tidak ada gambar/dokumen untuk seal kompatibel {tag}.", FACT, ())
            return CopilotAnswer(f"No drawings/documents found for {tag}'s compatible seals.", FACT, ())
        lines = [f"- {d.get('document_number') or d.get('drawing_id')}: {d.get('title') or 'N/A'} (rev {d.get('revision') or 'N/A'})" for d in drawings]
        if language == "id":
            answer = f"{len(drawings)} gambar/dokumen untuk {tag}:\n" + "\n".join(lines)
        else:
            answer = f"{len(drawings)} drawing(s)/document(s) for {tag}:\n" + "\n".join(lines)
        evidence = tuple(_evidence("SealEngineeringDocument", d.get("drawing_id") or tag, "revision", d.get("revision")) for d in drawings)
        return CopilotAnswer(answer, FACT, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Data gambar/dokumen untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Drawing/document data for {tag} is currently unavailable.", DATA_GAP, ())


def _handle_installation(tag: str, *, installation_gateway, language: str = "en", **_: Any) -> CopilotAnswer:
    response = installation_gateway.list_installations()
    if not response.get("success"):
        if language == "id":
            return CopilotAnswer(f"Data instalasi untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Installation data for {tag} is currently unavailable.", DATA_GAP, ())
    records = [r for r in (response.get("data") or []) if r.get("plant_equip_no") == tag]
    if not records:
        if language == "id":
            return CopilotAnswer(f"Tidak ada laporan instalasi untuk {tag}.", FACT, ())
        return CopilotAnswer(f"No installation report found for {tag}.", FACT, ())
    latest = records[-1]
    if language == "id":
        answer = f"{tag} memiliki {len(records)} laporan instalasi; terbaru: {latest.get('installation_code') or 'N/A'} tanggal {latest.get('report_date') or 'N/A'}."
    else:
        answer = f"{tag} has {len(records)} installation report(s); most recent: {latest.get('installation_code') or 'N/A'} dated {latest.get('report_date') or 'N/A'}."
    evidence = (_evidence("InstallationGateway", latest.get("installation_code") or tag, "report_date", latest.get("report_date")),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_latest_installation_fleet(
    scope: frozenset[str] | None, *, installation_report_repository, pump_gateway, language: str = "en", **_: Any
) -> CopilotAnswer:
    """Fleet-wide (no tag): "pompa mana yang terakhir dipasang?" and its
    semantic variants. Reads via installation_report_repository (direct-DB,
    MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A -- see that module's
    own header for why the n8n-backed InstallationGateway could not be used
    here), applies the caller's own Area/MA scope BEFORE selection (never
    after -- see maintenance_intelligence_service.select_latest_
    installation's own header), then defers to that pure, already-tested
    selector. Never invents an installation: an empty/undated result is a
    truthful DATA_GAP, never a fabricated pump/date."""
    response = installation_report_repository.list_installations()
    if not response.get("success"):
        if language == "id":
            return CopilotAnswer("Data instalasi sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer("Installation data is currently unavailable.", DATA_GAP, ())

    records = response.get("data") or []
    if scope is not None:
        records = filter_records_by_asset_scope(records, scope, pump_gateway, asset_field="plant_equip_no")

    latest = mis.select_latest_installation(records)
    if latest is None:
        if language == "id":
            return CopilotAnswer(
                "Belum ada riwayat instalasi dengan tanggal tercatat.", DATA_GAP, (),
            )
        return CopilotAnswer(
            "No installation history with a recorded date is available -- installation history is absent.",
            DATA_GAP,
            (),
        )

    tag = latest.get("plant_equip_no") or "N/A"
    seal_code = latest.get("seal_code")
    seal_type = latest.get("seal_type")
    if language == "id":
        if seal_code:
            seal_clause = f", seal {seal_code}" + (f" ({seal_type})" if seal_type else "")
        else:
            seal_clause = ", seal belum tercatat"
        answer = (
            f"Pompa yang terakhir dipasang adalah {tag} (laporan instalasi "
            f"{latest.get('installation_code') or 'N/A'}, tanggal {latest.get('report_date') or 'N/A'}"
            f"{seal_clause})."
        )
    else:
        if seal_code:
            seal_clause = f", seal {seal_code}" + (f" ({seal_type})" if seal_type else "")
        else:
            seal_clause = ", seal not recorded"
        answer = (
            f"The most recently installed pump is {tag} (installation report "
            f"{latest.get('installation_code') or 'N/A'}, dated {latest.get('report_date') or 'N/A'}"
            f"{seal_clause})."
        )
    evidence = (
        _evidence("InstallationReportRepository", latest.get("installation_code") or tag, "report_date", latest.get("report_date")),
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_condition_monitoring(
    tag: str, *, condition_monitoring_reading_repository, language: str = "en", **_: Any
) -> CopilotAnswer:
    """Tag-scoped: "ada temuan terbaru di <tag>?" / "CMON terakhir <tag>
    apa?". Reads via condition_monitoring_reading_repository (direct-DB,
    the same canonical repository the WhatsApp/dashboard CMON WRITE flow
    already persists through -- read-only here, list_by_asset() only,
    never create_draft/update_draft/submit/etc.). Its own ORDER BY
    reading_date DESC NULLS LAST, created_at DESC already selects the
    newest reading as records[0] -- no re-sorting here. Only canonical
    columns are surfaced (reading_date, finding, workflow_status,
    technical_recommendation, source_reference); a field this table has
    no value for is omitted, never invented."""
    # Everything downstream (not just the repository call itself) is
    # inside this try: a mis-shaped/unexpected result (e.g. a dict
    # instead of a list, per-record dicts missing .get()) must degrade to
    # DATA_GAP exactly like a genuine connection failure, never propagate
    # as an unhandled 500 to the WhatsApp caller.
    try:
        records = condition_monitoring_reading_repository.list_by_asset(tag)
        if not isinstance(records, list):
            if language == "id":
                return CopilotAnswer(f"Data Condition Monitoring untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
            return CopilotAnswer(f"Condition Monitoring data for {tag} is currently unavailable.", DATA_GAP, ())
        if not records:
            if language == "id":
                return CopilotAnswer(f"Belum ada data Condition Monitoring untuk {tag}.", FACT, ())
            return CopilotAnswer(f"No Condition Monitoring data found for {tag}.", FACT, ())

        latest = records[0]
        if language == "id":
            lines = [tag, "", f"CMON terakhir: {latest.get('reading_date') or 'tidak diketahui'}"]
            lines.append(f"Temuan: {latest.get('finding') or 'tidak ada catatan'}")
            status = latest.get("workflow_status")
            if status:
                lines.append(f"Status: {status}")
            recommendation = latest.get("technical_recommendation")
            if recommendation:
                lines.append(f"Rekomendasi: {recommendation}")
            source_reference = latest.get("source_reference")
            if source_reference:
                lines.append(f"Sumber: {source_reference}")
        else:
            lines = [tag, "", f"Latest CMON: {latest.get('reading_date') or 'unknown'}"]
            lines.append(f"Finding: {latest.get('finding') or 'no record'}")
            status = latest.get("workflow_status")
            if status:
                lines.append(f"Status: {status}")
            recommendation = latest.get("technical_recommendation")
            if recommendation:
                lines.append(f"Recommendation: {recommendation}")
            source_reference = latest.get("source_reference")
            if source_reference:
                lines.append(f"Source: {source_reference}")

        answer = "\n".join(lines)
        evidence = (
            _evidence(
                "ConditionMonitoringReadingRepository",
                latest.get("condition_monitoring_reading_code") or tag,
                "finding",
                latest.get("finding"),
            ),
        )
        return CopilotAnswer(answer, FACT, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Data Condition Monitoring untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Condition Monitoring data for {tag} is currently unavailable.", DATA_GAP, ())


def _handle_leak_frequency_fleet(
    scope: frozenset[str] | None, *, condition_monitoring_reading_gateway, pump_gateway, language: str = "en", **_: Any
) -> CopilotAnswer:
    """Fleet-wide (no tag): "pompa mana yang paling sering bocor?" --
    aggregates mechanical-seal-leak-flagged condition_monitoring_reading
    records (the same DE/NDE flags get_pump_condition_monitoring_flag
    already reads for a single tag), never Corrective Maintenance (CM)
    records -- see this module's own "CM Is a Terminology Collision" note
    in _detect_intent's header."""
    response = condition_monitoring_reading_gateway.list_condition_monitoring_readings()
    if not response.get("success"):
        if language == "id":
            return CopilotAnswer("Data condition monitoring sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer("Condition monitoring data is currently unavailable.", DATA_GAP, ())

    records = response.get("data") or []
    if scope is not None:
        records = filter_records_by_asset_scope(records, scope, pump_gateway)

    result = mis.select_most_frequent_leak_pump(records)
    if result is None:
        if language == "id":
            return CopilotAnswer(
                "Belum ada kebocoran mechanical seal yang tercatat pada data condition monitoring.", DATA_GAP, ()
            )
        return CopilotAnswer(
            "No mechanical seal leak has been recorded in condition monitoring readings.", DATA_GAP, ()
        )

    tag, leak_count = result
    answer = f"{tag} has the most recorded mechanical seal leak readings ({leak_count})."
    evidence = (_evidence("ConditionMonitoringReadingGateway", tag, "mechanical_seal_leak_count", leak_count),)
    return CopilotAnswer(answer, FACT, evidence)


# Stock V1's own null/0/positive quantity_available contract (MWO-LTSA-
# AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A's explicit rule) -- rendered
# once here so both the single-pool and multi-pool answers below phrase it
# identically, never two different wordings for the same underlying state.
def _quantity_available_phrase(quantity: Any, language: str = "en") -> str:
    if language == "id":
        if quantity is None:
            return "jumlah stok tidak diketahui"
        if quantity == 0:
            return "stok habis (0 tersedia)"
        return f"{quantity} unit tersedia"
    if quantity is None:
        return "stock quantity unknown"
    if quantity == 0:
        return "out of stock (0 available)"
    return f"{quantity} unit(s) available"


def _handle_stock_by_seal_code(
    seal_code: str, *, mechanical_seal_stock_repository, language: str = "en", **_: Any
) -> CopilotAnswer:
    """Seal-code-keyed Stock V1 lookup, no pump tag needed ("stok seal
    T48MP ada berapa?"). Reads ONLY mechanical_seal_stock_pool (via the
    already-existing, unmodified MechanicalSealStockRepository.list_pools()
    -- no new SQL) -- legacy seal_stock is not wired into this handler at
    all (MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A). quantity_available
    is the authoritative field (the same one the Mechanical Seal Stock /
    Asset 360 "Seal Stock Available" UI already surfaces as "Available" --
    never quantity_on_hand, which does not net out reservations).
    list_pools()'s own `search` filter does not match on seal_code, so
    every pool is fetched (44 real pools today, comfortably under the 200
    cap) and filtered here -- reuse of the existing method, not a
    duplicated query."""
    response = mechanical_seal_stock_repository.list_pools(limit=200)
    if not response.get("success"):
        if language == "id":
            return CopilotAnswer(f"Data stok untuk seal {seal_code} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Stock data for seal {seal_code} is currently unavailable.", DATA_GAP, ())

    pools = mis.select_stock_v1_pools_by_seal_code(response.get("data") or [], seal_code)
    if not pools:
        if language == "id":
            return CopilotAnswer(f"Tidak ada catatan Stock V1 untuk seal {seal_code}.", DATA_GAP, ())
        return CopilotAnswer(f"No Stock V1 record found for seal {seal_code}.", DATA_GAP, ())

    if len(pools) == 1:
        pool = pools[0]
        quantity = pool.get("quantity_available")
        # No EN/ID branching needed here -- the only language-dependent
        # fragment is _quantity_available_phrase's own return value.
        answer = f"Seal {seal_code} (stock pool {pool.get('stock_pool_id') or 'N/A'}): {_quantity_available_phrase(quantity, language)}."
        evidence = (_evidence("MechanicalSealStockV1", pool.get("stock_pool_id") or seal_code, "quantity_available", quantity),)
        return CopilotAnswer(answer, FACT, evidence)

    # Multiple Stock V1 pools for one seal_code -- reported separately,
    # never summed (no existing Stock V1 contract declares this additive).
    if language == "id":
        lines = [
            f"- pool {pool.get('stock_pool_id') or 'N/A'}: {_quantity_available_phrase(pool.get('quantity_available'), language)} "
            f"({pool.get('stock_location') or 'lokasi tidak tercatat'})"
            for pool in pools
        ]
        answer = f"Seal {seal_code} memiliki {len(pools)} Stock V1 pool terpisah:\n" + "\n".join(lines)
    else:
        lines = [
            f"- pool {pool.get('stock_pool_id') or 'N/A'}: {_quantity_available_phrase(pool.get('quantity_available'), language)} "
            f"({pool.get('stock_location') or 'location not recorded'})"
            for pool in pools
        ]
        answer = f"Seal {seal_code} has {len(pools)} separate Stock V1 pools:\n" + "\n".join(lines)
    evidence = tuple(
        _evidence("MechanicalSealStockV1", pool.get("stock_pool_id") or seal_code, "quantity_available", pool.get("quantity_available"))
        for pool in pools
    )
    return CopilotAnswer(answer, FACT, evidence)


_FLEET_STOCK_PREDICATE_LABEL = {
    "en": {
        "OUT_OF_STOCK": "have seal stock recorded as 0",
        "UNKNOWN_STOCK": "have unknown seal stock quantity",
        "AVAILABLE_STOCK": "have seal stock available",
        "LOWEST_STOCK": "share the lowest recorded seal stock quantity",
    },
    "id": {
        "OUT_OF_STOCK": "memiliki stok seal tercatat 0",
        "UNKNOWN_STOCK": "memiliki jumlah stok seal tidak diketahui",
        "AVAILABLE_STOCK": "memiliki stok seal tersedia",
        "LOWEST_STOCK": "memiliki jumlah stok seal terendah",
    },
}


def _handle_fleet_stock_status(
    question: str,
    scope: frozenset[str] | None,
    *,
    mechanical_seal_stock_repository,
    pump_gateway,
    language: str = "en",
    **_: Any,
) -> CopilotAnswer:
    """Fleet-wide (no tag, no seal code): "seal pompa mana yang ga ada
    stocknya?" and its semantic variants. Pump/seal/stock identity comes
    ONLY from each pool's own real `applications` list (Stock V1's
    authoritative application->pool mapping, reused unmodified via
    mis.flatten_stock_v1_fleet_rows) -- never inferred from two pools
    sharing a similar seal description. Area/MA scope is applied to the
    flattened rows BEFORE predicate selection, never after."""
    response = mechanical_seal_stock_repository.list_pools(limit=200)
    if not response.get("success"):
        if language == "id":
            return CopilotAnswer("Data Stock V1 sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer("Stock V1 data is currently unavailable.", DATA_GAP, ())

    rows = mis.flatten_stock_v1_fleet_rows(response.get("data") or [])
    if scope is not None:
        rows = filter_records_by_asset_scope(rows, scope, pump_gateway, asset_field="equipment_tag")

    predicate = _detect_fleet_stock_predicate(question)
    matches = mis.select_fleet_stock_by_predicate(rows, predicate)
    label = _FLEET_STOCK_PREDICATE_LABEL[language][predicate]

    if not matches:
        if language == "id":
            return CopilotAnswer(f"Tidak ada pompa yang {label}.", DATA_GAP, ())
        return CopilotAnswer(f"No pumps found that {label}.", DATA_GAP, ())

    if language == "id":
        lines = [
            f"- {row['equipment_tag']} — {row['seal_type'] or 'N/A'} — "
            f"{row['quantity_available'] if row['quantity_available'] is not None else 'tidak diketahui'}"
            for row in matches
        ]
        answer = f"{len(matches)} pompa {label}:\n" + "\n".join(lines)
    else:
        lines = [
            f"- {row['equipment_tag']} — {row['seal_type'] or 'N/A'} — "
            f"{row['quantity_available'] if row['quantity_available'] is not None else 'unknown'}"
            for row in matches
        ]
        answer = f"{len(matches)} pump(s) {label}:\n" + "\n".join(lines)
    evidence = tuple(
        _evidence(
            "MechanicalSealStockV1",
            row["stock_pool_id"] or row["equipment_tag"],
            "quantity_available",
            row["quantity_available"],
        )
        for row in matches
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_recommendation(tag: str, *, ltsa_knowledge_service, language: str = "en", **_: Any) -> CopilotAnswer:
    try:
        knowledge = ltsa_knowledge_service.build(tag)
        recommendations = knowledge.recommendation or ()
        if not recommendations:
            if language == "id":
                return CopilotAnswer(f"Tidak ada rekomendasi aktif untuk {tag}.", FACT, ())
            return CopilotAnswer(f"No active recommendations for {tag}.", FACT, ())
        top = recommendations[0]
        lines = [f"- [{rec.category}] {rec.title}: {rec.action}" for rec in recommendations]
        if language == "id":
            answer = f"{len(recommendations)} rekomendasi untuk {tag} (utama: {top.title}):\n" + "\n".join(lines)
        else:
            answer = f"{len(recommendations)} recommendation(s) for {tag} (top: {top.title}):\n" + "\n".join(lines)
        evidence = tuple(_evidence(ev.source, ev.reference, ev.field, ev.value) for rec in recommendations for ev in rec.evidence)
        return CopilotAnswer(answer, RECOMMENDATION, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Data rekomendasi untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Recommendation data for {tag} is currently unavailable.", DATA_GAP, ())


def _handle_fleet_priority(
    scope: frozenset[str] | None, *, fleet_executive_summary_service, language: str = "en", **_: Any
) -> CopilotAnswer:
    """Fleet-wide, tag-less by construction (there is no meaningful
    per-pump "priority" tool -- ranking is inherently across many pumps):
    "pompa mana yang perlu perhatian hari ini?" / "pompa paling kritis
    apa?". Reuses FleetExecutiveSummaryService.build(scope=...) unchanged
    -- the exact same canonical ranking routers/fleet.py's own
    /api/ltsa/fleet/powerbi endpoint already serves, built from
    FleetReliabilityService + RecommendationEngine, never a new scoring
    formula. scope is applied INSIDE build() at pump discovery (see that
    service's own docstring) -- an authorized caller's ranking is
    genuinely recomputed from only their pumps, never a global ranking
    filtered/hidden after the fact."""
    # Everything downstream (not just build() itself) is inside this try:
    # a mis-shaped/unexpected result must degrade to DATA_GAP exactly like
    # a genuine service failure, never propagate as an unhandled 500 to
    # the WhatsApp caller.
    try:
        summary = fleet_executive_summary_service.build(scope=scope)
        top_risks = getattr(summary, "top_risks", None) or ()
        if not top_risks:
            if language == "id":
                return CopilotAnswer("Tidak ada pompa yang saat ini perlu perhatian dalam cakupan otorisasi Anda.", FACT, ())
            return CopilotAnswer("No pumps currently need attention in your authorized scope.", FACT, ())

        fleet_status = getattr(summary, "fleet_status", None) or "UNKNOWN"
        if language == "id":
            lines = [f"- {risk.tag_number}: {risk.title} (priority {risk.priority}) -- {risk.action}" for risk in top_risks]
            answer = (
                f"{len(top_risks)} pompa perlu perhatian dalam cakupan otorisasi Anda "
                f"(status fleet: {fleet_status}):\n" + "\n".join(lines)
            )
        else:
            lines = [f"- {risk.tag_number}: {risk.title} (priority {risk.priority}) -- {risk.action}" for risk in top_risks]
            answer = (
                f"{len(top_risks)} pump(s) needing attention in your authorized scope "
                f"(fleet status: {fleet_status}):\n" + "\n".join(lines)
            )
        evidence = tuple(
            _evidence("FleetExecutiveSummaryService", risk.tag_number, "priority", risk.priority) for risk in top_risks
        )
        return CopilotAnswer(answer, RECOMMENDATION, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer("Data prioritas fleet sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer("Fleet priority data is currently unavailable.", DATA_GAP, ())


# MWO-AI5R-LTSA-AI-ORCHESTRATION-001 -- exported (was module-private) so
# copilot_orchestrator.py can expose these exact same functions as
# AI-selectable TOOLS, without duplicating a single one of them. The
# orchestrator only ever picks a NAME from this dict's own keys (validated
# against its own fixed catalog before any call) -- an LLM can select
# which tool to run, never inject new code, arguments, or a query string.
TOOL_HANDLERS = {
    "pump_status": _handle_pump_status,
    "pump_history": _handle_pump_history,
    "work_orders": _handle_work_orders,
    "pm": _handle_pm,
    "cm": _handle_cm,
    "current_seal": _handle_current_seal,
    "seal_compat": _handle_seal_compat,
    "inventory": _handle_inventory,
    "drawing_document": _handle_drawing_document,
    "installation": _handle_installation,
    "recommendation": _handle_recommendation,
    "condition_monitoring": _handle_condition_monitoring,
}


__all__ = [
    "CopilotAnswer", "ask_copilot", "TOOL_HANDLERS",
    "FACT", "INTERPRETATION", "RECOMMENDATION", "DATA_GAP",
]

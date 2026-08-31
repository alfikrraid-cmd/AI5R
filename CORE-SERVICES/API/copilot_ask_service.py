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

from . import fleet_analytics_service as fas
from . import maintenance_intelligence_service as mis
from .condition_monitoring_measurement_fields import (
    detect_parameter_search_term,
    fields_matching_search_term,
    parameter_display_label,
    parameter_values,
    render_parameter_lines,
    render_reading_lines,
)
from .condition_monitoring_time_range import parse_condition_monitoring_period
from .pump_area_scope import filter_records_by_asset_scope
from .seal_leak_diagnostic_service import DATA_GAP as DIAGNOSTIC_DATA_GAP
from .seal_leak_diagnostic_service import SealLeakDiagnosis

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
def _detect_intent(question: str, *, tag: str | None = None) -> str | None:
    q = (question or "").lower()

    def has(*words: str) -> bool:
        return any(re.search(word, q) for word in words)

    is_current_or_latest = has("current", "terakhir", "latest", "terbaru", "most recent", "sekarang", r"\bnow\b")
    is_install_or_replace_wording = has(
        "install", "pasang", "dipasang", "pemasangan", "ganti", "diganti", "replace", "replacement"
    )
    is_fleet_question = has(r"pompa\s+mana", r"pump\s+mana", r"which\s+pump")
    is_diagnostic_question = has("kenapa", "mengapa", "analisa", "analisis", "diagnosa", "diagnose", "diagnostic", "penyebab", "cause", "why")

    if re.search(r"^\s*pm\b", q):
        return "pm"
    if re.search(r"^\s*cm\b", q):
        return "cm"

    if has(r"\bseal\b", r"\bsegel\b") and is_current_or_latest and not is_install_or_replace_wording:
        return "current_seal"
    if has("install", "pasang", "dipasang", "pemasangan") or (
        has(r"\bseal\b", r"\bsegel\b") and has("ganti", "diganti", "replace", "replacement")
    ):
        return "installation"
    # MWO-LTSA-EQUIPMENT-360-CANONICAL-001 -- generic CMON parameter
    # wording (temperature/suhu, vibration/getaran, pressure/tekanan)
    # routes to the SAME condition_monitoring intent/handler as
    # "cmon"/"bocor" -- the parameter data lives in the exact same
    # condition_monitoring_reading table, so no new intent/handler is
    # needed; _handle_condition_monitoring itself re-derives which
    # parameter was asked for from the raw question text. "current"/
    # "arus" (motor current) is deliberately excluded here -- seal
    # condition_monitoring_measurement_fields.py's own docstring for why
    # (collision with "current seal"/is_current_or_latest wording above).
    if has("bocor", r"\bleak") and tag is not None and is_diagnostic_question and not is_fleet_question:
        return "seal_leak_diagnostic"
    if has(
        "bocor", r"\bleak", r"\bcmon\b", "condition monitoring", "temuan",
        "temperature", "temperatur", "suhu", "vibration", "getaran", "pressure", "tekanan",
    ):
        return "condition_monitoring"
    # MWO-LTSA-FLEET-ANALYTICS-001 -- "overdue PM" is a fleet-wide,
    # tag-less ranking/listing question (Phase 12), checked before the
    # generic per-tag `pm` intent so it is never swallowed by it (a
    # tag-less "overdue PM?" would otherwise fall through to _NO_ASSET_
    # MESSAGE, since `pm` has no tag-less branch of its own).
    if has("overdue", "terlambat", "jatuh tempo") and has(r"\bpm\b", "preventive", "maintenance", "perawatan"):
        return "fleet_pm_overdue"
    if has(r"\bpm\b", "preventive"):
        return "pm"
    if has(r"\bcm\b", "corrective", "breakdown", "kerusakan", r"\brusak"):
        return "cm"
    if has("work order", "workorder", r"\bwo\b", "kerja"):
        return "work_orders"
    if has("stock", "stok", "inventory", "inventaris", "spare part", "sparepart", "spare seal", "suku cadang", "tersedia"):
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
    pm_occurrence_repository,
    cm_report_repository,
    pm_cm_evidence_repository=None,
    # MWO-LTSA-FLEET-ANALYTICS-001 -- optional, default None: only needed
    # by the new fleet-wide temperature/vibration ranking, current/
    # historical leak, stock-semantics, and overdue-PM query paths below,
    # each of which gracefully falls back to its pre-existing behavior
    # (or a plain DATA_GAP for a genuinely new capability) when any of
    # these three are absent -- every pre-existing caller/test that
    # doesn't supply them keeps its exact current behavior, unchanged.
    pm_schedule_repository=None,
    seal_pump_compatibility_gateway=None,
    seal_gateway=None,
    seal_leak_diagnostic_service=None,
    language: str = "en",
) -> CopilotAnswer:
    intent = _detect_intent(question, tag=tag)

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
        return _dispatch_fleet_condition_monitoring(
            question, scope,
            condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
            pump_gateway=pump_gateway,
            condition_monitoring_reading_repository=condition_monitoring_reading_repository,
            cm_report_repository=cm_report_repository,
            pm_occurrence_repository=pm_occurrence_repository,
            pm_schedule_repository=pm_schedule_repository,
            seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
            seal_gateway=seal_gateway,
            mechanical_seal_stock_repository=mechanical_seal_stock_repository,
            work_order_gateway=work_order_gateway,
            maintenance_history_gateway=maintenance_history_gateway,
            language=language,
        )

    if intent == "fleet_pm_overdue":
        return _handle_fleet_overdue_pm(
            scope,
            pump_gateway=pump_gateway,
            condition_monitoring_reading_repository=condition_monitoring_reading_repository,
            cm_report_repository=cm_report_repository,
            pm_occurrence_repository=pm_occurrence_repository,
            pm_schedule_repository=pm_schedule_repository,
            seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
            seal_gateway=seal_gateway,
            mechanical_seal_stock_repository=mechanical_seal_stock_repository,
            work_order_gateway=work_order_gateway,
            maintenance_history_gateway=maintenance_history_gateway,
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
        # MWO-LTSA-FLEET-ANALYTICS-001 -- Phase 9/10/11's explicit,
        # never-collapsed inventory states (ZERO_STOCK/NO_STOCK_RECORD/
        # NO_COMPATIBLE_SEAL, distinguished per equipment+seal, never one
        # generic "out of stock" bucket). Checked ONLY for the specific
        # phrasings _detect_fleet_stock_semantic recognizes (explicit
        # "record"/"catatan" wording, an explicit zero quantity, or "spare
        # seal" negated) -- every other fleet-stock phrasing (including
        # the pre-existing "ga ada stocknya"/"tidak ada stock"/"kosong"/
        # "unknown" wording _handle_fleet_stock_status already answers
        # correctly) is intentionally left on the unchanged path below, so
        # no pre-existing regression test's exact response format changes.
        semantic = _detect_fleet_stock_semantic(question)
        if semantic is not None:
            return _handle_fleet_stock_semantics(
                semantic, scope,
                pump_gateway=pump_gateway,
                condition_monitoring_reading_repository=condition_monitoring_reading_repository,
                cm_report_repository=cm_report_repository,
                pm_occurrence_repository=pm_occurrence_repository,
                pm_schedule_repository=pm_schedule_repository,
                seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
                seal_gateway=seal_gateway,
                mechanical_seal_stock_repository=mechanical_seal_stock_repository,
                work_order_gateway=work_order_gateway,
                maintenance_history_gateway=maintenance_history_gateway,
                language=language,
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
        question=question,
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
        pm_occurrence_repository=pm_occurrence_repository,
        cm_report_repository=cm_report_repository,
        pm_cm_evidence_repository=pm_cm_evidence_repository,
        seal_leak_diagnostic_service=seal_leak_diagnostic_service,
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


def _handle_pm(tag: str, *, pm_occurrence_repository, language: str = "en", **_: Any) -> CopilotAnswer:
    # MWO-LTSA-EQUIPMENT-360-001 -- reads via pm_occurrence_repository
    # (direct-DB, the SAME canonical repository the WhatsApp PM WRITE
    # flow already persists through), replacing the previous
    # mis.get_pump_last_pm(tag) call -- that function received no
    # gateway kwargs at all here, so it always constructed its OWN
    # default PMOccurrenceGateway/WorkOrderGateway/MaintenanceHistory
    # Gateway (n8n), a genuinely SEPARATE data path from what WhatsApp's
    # own canonical write just persisted. This is the root cause this
    # MWO's own audit traced for the "PM terakhir" contradiction: same
    # equipment, same database, two disconnected retrieval paths. Its own
    # ORDER BY occurrence_date DESC NULLS LAST, created_at DESC already
    # selects the newest occurrence as records[0] -- no re-sorting here.
    # workflow_status is surfaced truthfully (DRAFT stays DRAFT), never
    # silently promoted to a confirmed fact.
    try:
        records = pm_occurrence_repository.list_by_asset(tag)
        if not isinstance(records, list):
            if language == "id":
                return CopilotAnswer(f"Riwayat PM untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
            return CopilotAnswer(f"PM history for {tag} is currently unavailable.", DATA_GAP, ())
        if not records:
            if language == "id":
                return CopilotAnswer(f"Tidak ada catatan Preventive Maintenance (PM) untuk {tag}.", FACT, ())
            return CopilotAnswer(f"No preventive maintenance (PM) record found for {tag}.", FACT, ())

        last_pm = records[0]
        status = last_pm.get("workflow_status") or last_pm.get("status")
        if language == "id":
            answer = f"PM terakhir {tag} pada {last_pm.get('occurrence_date') or 'tanggal tidak diketahui'}"
            if status:
                answer += f" (status: {status})"
            answer += f", sumber: {last_pm.get('provenance') or 'N/A'}."
        else:
            answer = f"{tag}'s last PM was on {last_pm.get('occurrence_date') or 'an unknown date'}"
            if status:
                answer += f" (status: {status})"
            answer += f", source: {last_pm.get('provenance') or 'N/A'}."
        evidence = (
            _evidence("PMOccurrenceRepository", last_pm.get("pm_occurrence_code") or tag, "occurrence_date", last_pm.get("occurrence_date")),
        )
        return CopilotAnswer(answer, FACT, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Riwayat PM untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"PM history for {tag} is currently unavailable.", DATA_GAP, ())


def _handle_cm(tag: str, *, cm_report_repository, language: str = "en", **_: Any) -> CopilotAnswer:
    # MWO-LTSA-EQUIPMENT-360-001 -- reads via cm_report_repository
    # (direct-DB, the SAME canonical repository routers/cm_report.py's
    # own dashboard endpoint already depends on), replacing the previous
    # mis.get_pump_last_cm(tag) call -- that function received no gateway
    # kwarg here either, so it always constructed its own default
    # CMReportGateway (n8n), a separate path from the direct-DB
    # cm_report table. list_cm_reports() is already ORDER BY
    # COALESCE(failure_date, created_at) DESC -- filtering by asset_code
    # preserves that ordering, so the first match is still the newest.
    try:
        response = cm_report_repository.list_cm_reports()
        if not response.get("success"):
            if language == "id":
                return CopilotAnswer(f"Riwayat CM untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
            return CopilotAnswer(f"CM history for {tag} is currently unavailable.", DATA_GAP, ())
        records = [r for r in (response.get("data") or []) if r.get("asset_code") == tag]
        if not records:
            if language == "id":
                return CopilotAnswer(f"Tidak ada catatan Corrective Maintenance (CM) untuk {tag}.", FACT, ())
            return CopilotAnswer(f"No corrective maintenance (CM) record found for {tag}.", FACT, ())

        last_cm = records[0]
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
        evidence = (_evidence("CMReportRepository", last_cm.get("cm_report_code") or tag, "severity", last_cm.get("severity")),)
        return CopilotAnswer(answer, FACT, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Riwayat CM untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"CM history for {tag} is currently unavailable.", DATA_GAP, ())


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


def _seal_size_display(row: dict[str, Any]) -> str:
    # MWO-LTSA-STOCK-RESPONSE-STANDARD-001 -- nominal_size/size_unit are
    # Stock V1's own canonical structured size fields (mechanical_seal_
    # stock_pool.nominal_size/size_unit, already SELECTed by list_pools())
    # -- never derived by parsing seal_code/seal_type identifier strings
    # (e.g. "T6014DP" or "LTSA-SEAL-T6014DP-60MM" must NOT be parsed for
    # "60mm"). "N/A" whenever the canonical field itself is absent, the
    # field is never omitted.
    nominal_size = row.get("nominal_size")
    if nominal_size is None or str(nominal_size).strip() == "":
        return "N/A"
    size_unit = row.get("size_unit")
    if size_unit is None or str(size_unit).strip() == "":
        return str(nominal_size)
    return f"{nominal_size} {size_unit}"


def _installed_seal_line(tag: str, *, equipment_timeline_service, language: str = "en") -> str:
    # Compatible != installed (Hard Rule, unchanged from _handle_current_
    # seal): reads ONLY equipment_timeline_service.build_current_seal(tag),
    # the same identity-safe, evidence-required source -- never inferred
    # from the compatible-seal/stock list this handler already has.
    current_seal = None
    try:
        current_seal = equipment_timeline_service.build_current_seal(tag)
    except Exception:
        current_seal = None
    if current_seal is None:
        return "Installed seal: Belum terkonfirmasi" if language == "id" else "Installed seal: Not confirmed"
    label = "terkonfirmasi" if language == "id" else "confirmed"
    return f"Installed seal: {current_seal.seal_code or 'N/A'} ({label})"


def _handle_inventory(
    tag: str, *, mechanical_seal_stock_repository, equipment_timeline_service, language: str = "en", **_: Any
) -> CopilotAnswer:
    # MWO-LTSA-EQUIPMENT-360-001 -- reads via mechanical_seal_stock_
    # repository (Stock V1, direct-DB), replacing the previous
    # ltsa_knowledge_service.build(tag).inventory call -- LTSAKnowledge
    # Service constructs its OWN internal SealStockGateway (n8n, the
    # LEGACY seal_stock source) when not given one, a genuinely different
    # data path from Stock V1 -- the SAME "ONLY stock authority Copilot
    # reads from" _handle_stock_by_seal_code/_handle_fleet_stock_status
    # already established (MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-
    # 017A). A tag-scoped stock question must resolve through the exact
    # same authority a seal-code-keyed or fleet-wide stock question does,
    # never a second, disconnected number for "the same" stock.
    # flatten_stock_v1_fleet_rows reuses Stock V1's own real
    # (equipment_tag, pool) application mapping unmodified -- never
    # infers a pump's stock from a pool it has no real application row
    # for.
    #
    # MWO-LTSA-STOCK-RESPONSE-STANDARD-001 -- rewritten to the mission's
    # standard response shape: canonical tag/model/size/qty always shown,
    # location when available, installed-seal status always shown
    # (compatible != installed, never conflated). Zero stock is rendered
    # as "0 unit", never as "no compatible seal" (compatibility and
    # inventory availability are different facts) -- matches produce one
    # numbered block each, quantities from different seal models/sizes
    # are never combined.
    try:
        response = mechanical_seal_stock_repository.list_pools(limit=200)
        if not response.get("success"):
            if language == "id":
                return CopilotAnswer(f"Data stok suku cadang untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
            return CopilotAnswer(f"Spare-part stock data for {tag} is currently unavailable.", DATA_GAP, ())

        rows = mis.flatten_stock_v1_fleet_rows(response.get("data") or [])
        matches = [row for row in rows if row["equipment_tag"] == tag]
        if not matches:
            if language == "id":
                return CopilotAnswer(f"Tidak ada catatan stok suku cadang untuk seal kompatibel {tag}.", FACT, ())
            return CopilotAnswer(f"No spare-part stock records are registered for {tag}'s compatible seals.", FACT, ())

        installed_line = _installed_seal_line(tag, equipment_timeline_service=equipment_timeline_service, language=language)

        if len(matches) == 1:
            row = matches[0]
            qty = row["quantity_available"] if row["quantity_available"] is not None else "N/A"
            if language == "id":
                lines = [
                    f"Stock Mechanical Seal — {tag}",
                    "",
                    f"Seal: {row['seal_type'] or 'N/A'}",
                    f"Size: {_seal_size_display(row)}",
                    f"Stock tersedia: {qty} unit",
                    f"Lokasi: {row.get('stock_location') or 'N/A'}",
                    installed_line,
                    "",
                    "Source: LTSA canonical data",
                ]
            else:
                lines = [
                    f"Mechanical Seal Stock — {tag}",
                    "",
                    f"Seal: {row['seal_type'] or 'N/A'}",
                    f"Size: {_seal_size_display(row)}",
                    f"Stock available: {qty} unit",
                    f"Location: {row.get('stock_location') or 'N/A'}",
                    installed_line,
                    "",
                    "Source: LTSA canonical data",
                ]
        else:
            header = f"Stock Mechanical Seal — {tag}" if language == "id" else f"Mechanical Seal Stock — {tag}"
            lines = [header, ""]
            for index, row in enumerate(matches, start=1):
                qty = row["quantity_available"] if row["quantity_available"] is not None else "N/A"
                if language == "id":
                    lines.append(f"{index}. {row['seal_type'] or 'N/A'}")
                    lines.append(f"   Size: {_seal_size_display(row)}")
                    lines.append(f"   Stock: {qty} unit")
                    lines.append(f"   Lokasi: {row.get('stock_location') or 'N/A'}")
                else:
                    lines.append(f"{index}. {row['seal_type'] or 'N/A'}")
                    lines.append(f"   Size: {_seal_size_display(row)}")
                    lines.append(f"   Stock: {qty} unit")
                    lines.append(f"   Location: {row.get('stock_location') or 'N/A'}")
            lines.append("")
            lines.append(installed_line)
            lines.append("")
            lines.append("Source: LTSA canonical data")

        answer = "\n".join(lines)
        evidence = tuple(
            _evidence("MechanicalSealStockV1", row["stock_pool_id"] or tag, "quantity_available", row["quantity_available"])
            for row in matches
        )
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


# MWO-LTSA-CMON-DETAILED-HISTORY-001 -- how many CMON events a WhatsApp
# reply renders in full before switching to "N more" (Phase 9's own
# bounded-rendering requirement). No existing default history window/
# limit is defined anywhere in this codebase for CMON (confirmed by
# repository archaeology before writing this) -- this is a RENDER limit
# only (never a data-fetch filter: the full matching set is always
# queried/counted first), matching the mission's own literal example
# ("Menampilkan 10 terbaru").
CMON_HISTORY_RENDER_LIMIT = 10

_CMON_HISTORY_WORDS = ("riwayat", "history", "histori", "hasil", "data cmon", "data condition monitoring")


def _is_cmon_history_request(question: str) -> bool:
    lowered = (question or "").casefold()
    return any(word in lowered for word in _CMON_HISTORY_WORDS)


def _cmon_leak_flagged(record: dict[str, Any]) -> bool:
    return record.get("mechanical_seal_leak_de") is True or record.get("mechanical_seal_leak_nde") is True


def _cmon_leak_confirmed_absent(record: dict[str, Any]) -> bool:
    # Both sides explicitly recorded False -- a real "no leak" fact, never
    # inferred from a missing/NULL value (tri-state, MWO's own Phase 6
    # rule: NULL/unknown and confirmed-normal are not the same thing).
    return record.get("mechanical_seal_leak_de") is False and record.get("mechanical_seal_leak_nde") is False


def _handle_condition_monitoring(
    tag: str,
    *,
    condition_monitoring_reading_repository,
    question: str = "",
    pm_cm_evidence_repository=None,
    language: str = "en",
    **_: Any,
) -> CopilotAnswer:
    """Tag-scoped CMON query, three semantics (MWO-LTSA-CMON-DETAILED-
    HISTORY-001):
      LATEST  -- "CMON terakhir/terbaru <tag>" (no history/range wording):
                 unchanged single-record narrative, byte-identical to the
                 pre-existing behavior.
      HISTORY -- "riwayat/history CMON <tag>" or "hasil/data CMON <tag>"
                 with no explicit period: every matching event (bounded
                 only at render time, never at fetch time), detailed
                 per-event readings.
      TIME-RANGE -- an explicit period ("setahun terakhir", "3 bulan
                 terakhir", "sejak Januari 2026", "tahun 2026", parsed by
                 condition_monitoring_time_range.py): same detailed
                 rendering, filtered to the interpreted [start, end].

    Reads via condition_monitoring_reading_repository (direct-DB, the
    same canonical repository the WhatsApp/dashboard CMON WRITE flow
    already persists through, and the SAME repository LTSAKnowledgeService
    uses to populate knowledge.condition_monitoring_readings for
    RecommendationEngine's own historical-leak-evidence rule -- one
    canonical source, not two; see this MWO's own root-cause note: the
    previous single-record-only LATEST rendering was the actual gap, not
    a divergent data source). list_by_asset()'s own ORDER BY reading_date
    DESC NULLS LAST, created_at DESC is reused unchanged for both the
    LATEST (records[0]) and detailed (already-sorted, newest-first)
    paths. Only canonical columns are surfaced; a field this table has no
    value for is rendered N/A, never invented."""
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

        period = parse_condition_monitoring_period(question)
        is_history_request = period is not None or _is_cmon_history_request(question)

        # MWO-LTSA-EQUIPMENT-360-CANONICAL-001 Phase 6 -- a parameter word
        # (temperature/suhu/vibration/getaran/pressure/tekanan) scopes the
        # SAME LATEST/HISTORY/TIME-RANGE semantics above to one parameter
        # group, reusing the SAME already-fetched records -- no second
        # query, no new intent handler.
        search_term = detect_parameter_search_term(question)
        if search_term is not None:
            fields = fields_matching_search_term(search_term)
            if not fields:
                if language == "id":
                    return CopilotAnswer(f"Data parameter tersebut tidak tersedia untuk {tag}.", DATA_GAP, ())
                return CopilotAnswer(f"That parameter is not available for {tag}.", DATA_GAP, ())
            return _render_cmon_parameter(
                tag, records, period, fields, search_term,
                history=is_history_request, language=language,
            )

        if not is_history_request:
            return _render_cmon_latest(tag, records, language=language)
        return _render_cmon_detailed_history(
            tag, records, period,
            pm_cm_evidence_repository=pm_cm_evidence_repository,
            language=language,
        )
    except Exception:
        if language == "id":
            return CopilotAnswer(f"Data Condition Monitoring untuk {tag} sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer(f"Condition Monitoring data for {tag} is currently unavailable.", DATA_GAP, ())


def _render_cmon_latest(tag: str, records: list[dict[str, Any]], *, language: str = "en") -> CopilotAnswer:
    # Byte-identical to the pre-MWO-LTSA-CMON-DETAILED-HISTORY-001
    # rendering -- regression-safety for every existing LATEST-query test.
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


def _render_cmon_parameter(
    tag: str,
    records: list[dict[str, Any]],
    period,
    fields: list[Any],
    search_term: str,
    *,
    history: bool,
    language: str = "en",
) -> CopilotAnswer:
    """MWO-LTSA-EQUIPMENT-360-CANONICAL-001 Phase 6 -- generic parameter-
    level CMON retrieval (temperature/vibration/pressure/...), LATEST or
    HISTORY/TIME-RANGE, reusing the exact same already-fetched records
    _handle_condition_monitoring's own LATEST/HISTORY paths use. Every
    value rendered is read straight from the canonical record; deterministic
    latest/min/max/delta in HISTORY mode are computed only from those same
    real values -- no LLM, no estimation."""
    if period is not None:
        matching = [
            r for r in records
            if (d := _parse_reading_date(r.get("reading_date"))) is not None and period.start <= d <= period.end
        ]
    else:
        matching = list(records)

    if not matching:
        if period is not None:
            if language == "id":
                answer = f"Tidak ditemukan data CMON {tag} pada periode {period.start.isoformat()} – {period.end.isoformat()}."
            else:
                answer = f"No CMON data found for {tag} in the period {period.start.isoformat()} – {period.end.isoformat()}."
        else:
            answer = f"Tidak ditemukan data CMON {tag}." if language == "id" else f"No CMON data found for {tag}."
        return CopilotAnswer(answer, FACT, ())

    if not history:
        # Most recent record that actually carries a value for this
        # parameter -- never assumed to be matching[0] (the newest EVENT
        # overall may not have this specific parameter recorded, while an
        # only-slightly-older one does; never silently reports "no data"
        # when a real, slightly older value exists).
        record = next((r for r in matching if parameter_values(r, fields)), None)
        if record is None:
            if language == "id":
                return CopilotAnswer(f"Belum ada nilai terekam untuk parameter tersebut pada {tag}.", FACT, ())
            return CopilotAnswer(f"No recorded value exists for that parameter on {tag}.", FACT, ())

        lines = render_parameter_lines(record, fields)
        header_label = parameter_display_label(search_term)
        reading_date = record.get("reading_date") or ("tidak diketahui" if language == "id" else "unknown")
        answer = "\n".join([f"{header_label} {tag}", f"Reading: {reading_date}", "", *lines])
        evidence = tuple(
            _evidence("ConditionMonitoringReadingRepository", record.get("condition_monitoring_reading_code") or tag, name, value)
            for name, value, _unit in parameter_values(record, fields)
        )
        return CopilotAnswer(answer, FACT, evidence)

    # HISTORY / TIME-RANGE parameter mode -- chronological listing +
    # deterministic latest/min/max/delta per parameter label.
    shown = matching[:CMON_HISTORY_RENDER_LIMIT]
    header_prefix = f"{parameter_display_label(search_term)} {tag}"
    if period is not None:
        period_label = period.label_id if language == "id" else period.label_en
        header = f"{header_prefix} — {period_label}"
    else:
        header = f"{header_prefix} — Riwayat" if language == "id" else f"{header_prefix} — History"

    lines = [header]
    if period is not None:
        lines.append(f"Periode: {period.start.isoformat()} – {period.end.isoformat()}")
    lines.append("")
    if len(matching) > len(shown):
        if language == "id":
            lines.append(f"Ditemukan {len(matching)} CMON. Menampilkan {len(shown)} terbaru.")
        else:
            lines.append(f"Found {len(matching)} CMON record(s). Showing {len(shown)} most recent.")
        lines.append("")

    series_by_label: dict[str, list[tuple[Any, float, str]]] = {}
    for record in shown:
        reading_date = record.get("reading_date") or ("tidak diketahui" if language == "id" else "unknown")
        values = parameter_values(record, fields)
        if values:
            lines.append(f"{reading_date}:")
            for name, value, unit in values:
                lines.append(f"   {name}: {value} {unit}")
                series_by_label.setdefault(name, []).append((record.get("reading_date"), value, unit))
        else:
            lines.append(f"{reading_date}: N/A")
        lines.append("")

    # Deterministic summary -- only over records actually carrying a real
    # value, only real arithmetic, never an LLM estimate.
    summary_header = "Ringkasan:" if language == "id" else "Summary:"
    lines.append(summary_header)
    for name, series in series_by_label.items():
        values_only = [v for _d, v, _u in series]
        unit = series[0][2]
        latest_value = series[0][1]  # shown is already newest-first
        lines.append(
            f"{name}: latest {latest_value} {unit}, min {min(values_only)} {unit}, max {max(values_only)} {unit}"
        )
    lines.append("")
    lines.append("Source: LTSA canonical data" if language != "id" else "Sumber: Data kanonik LTSA")

    answer = "\n".join(lines).rstrip()
    evidence = tuple(
        _evidence("ConditionMonitoringReadingRepository", record.get("condition_monitoring_reading_code") or tag, name, value)
        for record in shown
        for name, value, _unit in parameter_values(record, fields)
    )
    return CopilotAnswer(answer, FACT, evidence)


def _parse_reading_date(value: Any) -> Any:
    if not value:
        return None
    try:
        from datetime import date as _date
        return _date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _render_cmon_detailed_history(
    tag: str,
    records: list[dict[str, Any]],
    period,
    *,
    pm_cm_evidence_repository=None,
    language: str = "en",
) -> CopilotAnswer:
    if period is not None:
        matching = [
            r for r in records
            if (d := _parse_reading_date(r.get("reading_date"))) is not None and period.start <= d <= period.end
        ]
    else:
        matching = list(records)

    period_line = None
    if period is not None:
        label = period.label_id if language == "id" else period.label_en
        header = f"CMON {tag} — {label}"
        period_line = f"Periode: {period.start.isoformat()} – {period.end.isoformat()}"
    else:
        header = f"CMON {tag} — Riwayat" if language == "id" else f"CMON {tag} — History"

    if not matching:
        if period is not None:
            if language == "id":
                answer = f"Tidak ditemukan data CMON {tag} pada periode {period.start.isoformat()} – {period.end.isoformat()}."
            else:
                answer = f"No CMON data found for {tag} in the period {period.start.isoformat()} – {period.end.isoformat()}."
        else:
            if language == "id":
                answer = f"Tidak ditemukan data CMON {tag}."
            else:
                answer = f"No CMON data found for {tag}."
        return CopilotAnswer(answer, FACT, ())

    event_count = len(matching)
    shown = matching[:CMON_HISTORY_RENDER_LIMIT]
    reading_count = sum(len(render_reading_lines(r)) for r in matching)
    leak_count = sum(1 for r in matching if _cmon_leak_flagged(r))
    abnormal_count = leak_count
    normal_count = sum(1 for r in matching if _cmon_leak_confirmed_absent(r) and not _cmon_leak_flagged(r))
    latest_date = matching[0].get("reading_date")

    lines = [header]
    if period_line:
        lines.append(period_line)
    lines.append("")
    if event_count > len(shown):
        if language == "id":
            lines.append(f"Ditemukan {event_count} CMON. Menampilkan {len(shown)} terbaru.")
        else:
            lines.append(f"Found {event_count} CMON record(s). Showing {len(shown)} most recent.")
        lines.append("")

    for index, record in enumerate(shown, start=1):
        lines.append(f"{index}. {record.get('reading_date') or ('tidak diketahui' if language == 'id' else 'unknown')}")
        status = record.get("workflow_status")
        lines.append(f"   Status: {status or 'N/A'}")
        lines.append("")
        reading_lines = render_reading_lines(record)
        lines.append("   Readings:" if language != "id" else "   Readings:")
        if reading_lines:
            for reading_line in reading_lines:
                lines.append(f"   • {reading_line}")
        else:
            lines.append("   • N/A")
        lines.append("")
        finding_label = "Finding:" if language != "id" else "Finding:"
        lines.append(f"   {finding_label}")
        lines.append(f"   {record.get('finding') or 'N/A'}")
        lines.append("")
        # No canonical field distinct from `finding` exists for a
        # separate "observation" concept (confirmed by schema archaeology
        # -- CANONICAL_SCHEMA.sql's condition_monitoring_reading has no
        # such column). Always N/A, never repurposing technical_comment
        # (a review-stage field with its own distinct provenance) to fill
        # this section -- that would misrepresent its source, the same
        # fabrication this MWO explicitly forbids.
        lines.append("   Observation:")
        lines.append("   N/A")

        if pm_cm_evidence_repository is not None:
            try:
                attachments = pm_cm_evidence_repository.list_for_record(
                    "CONDITION_MONITORING_READING", record.get("condition_monitoring_reading_code")
                )
            except Exception:
                attachments = None
            if attachments:
                lines.append("")
                lines.append("   Dokumen:" if language == "id" else "   Document:")
                for attachment in attachments:
                    category = attachment.get("category")
                    suffix = f" ({category})" if category else ""
                    lines.append(f"   • {attachment.get('file_name') or 'N/A'}{suffix}")
        lines.append("")

    if language == "id":
        lines.append("Ringkasan:")
        lines.append(f"Total CMON: {event_count}")
        lines.append(f"Normal: {normal_count}")
        lines.append(f"Abnormal: {abnormal_count}")
        lines.append(f"Mechanical seal leak: {leak_count}")
        lines.append(f"CMON terakhir: {latest_date or 'tidak diketahui'}")
        lines.append("")
        lines.append("Sumber: Data kanonik LTSA")
    else:
        lines.append("Summary:")
        lines.append(f"Total CMON: {event_count}")
        lines.append(f"Normal: {normal_count}")
        lines.append(f"Abnormal: {abnormal_count}")
        lines.append(f"Mechanical seal leak: {leak_count}")
        lines.append(f"Latest CMON: {latest_date or 'unknown'}")
        lines.append("")
        lines.append("Source: LTSA canonical data")

    answer = "\n".join(lines).rstrip()
    # MWO-LTSA-CMON-DETAILED-HISTORY-001 Phase 5 -- CMON_EVENT_COUNT
    # (one entry per condition_monitoring_reading row -- an "inspection
    # event") is kept explicitly distinct from CMON_READING_COUNT (the
    # total count of individual non-null parameter VALUES across those
    # same events -- one event commonly carries many readings). Exposed
    # as evidence (machine-checkable, e.g. by this module's own tests)
    # rather than prose, keeping the WhatsApp reply itself concise per
    # this MWO's own Phase 9 bounded-rendering rule.
    evidence = (
        _evidence("ConditionMonitoringReadingRepository", tag, "cmon_event_count", event_count),
        _evidence("ConditionMonitoringReadingRepository", tag, "cmon_reading_count", reading_count),
    ) + tuple(
        _evidence(
            "ConditionMonitoringReadingRepository",
            record.get("condition_monitoring_reading_code") or tag,
            "finding",
            record.get("finding"),
        )
        for record in shown
    )
    return CopilotAnswer(answer, FACT, evidence)


# -- MWO-LTSA-FLEET-ANALYTICS-001: fleet-wide parameter ranking / current
# vs. historical leak / stock-semantics / overdue-PM ----------------------
#
# All four query shapes below read from ONE fleet_analytics_service.
# FleetDataBatch, fetched exactly once per question (never per pump) via
# _build_fleet_batch_or_none(). Every handler degrades to a plain
# DATA_GAP (never an exception) when the batch dependencies are not
# wired for a given caller -- see _build_fleet_batch_or_none's own
# docstring for why this is safe/backward-compatible.


def _build_fleet_batch_or_none(scope: frozenset[str] | None, **deps: Any) -> "fas.FleetDataBatch | None":
    """None (never raises) when any REQUIRED batch-fetch dependency
    (pump_gateway/condition_monitoring_reading_repository/cm_report_
    repository/pm_occurrence_repository/pm_schedule_repository/seal_
    pump_compatibility_gateway/seal_gateway/mechanical_seal_stock_
    repository) is absent -- e.g. an older caller/test that only supplies
    ask_copilot()'s pre-existing parameters, since pm_schedule_repository/
    seal_pump_compatibility_gateway/seal_gateway all default to None.
    Every new fleet-analytics handler treats a None batch as "this
    capability isn't wired here yet", never a crash -- and, for the two
    query shapes (leak/stock) that already had a pre-existing fleet-wide
    answer, the caller falls back to that unchanged behavior instead."""
    required = (
        deps.get("pump_gateway"),
        deps.get("condition_monitoring_reading_repository"),
        deps.get("cm_report_repository"),
        deps.get("pm_occurrence_repository"),
        deps.get("pm_schedule_repository"),
        deps.get("seal_pump_compatibility_gateway"),
        deps.get("seal_gateway"),
        deps.get("mechanical_seal_stock_repository"),
    )
    if any(dep is None for dep in required):
        return None
    try:
        return fas.build_fleet_data_batch(
            pump_gateway=deps["pump_gateway"],
            condition_monitoring_reading_repository=deps["condition_monitoring_reading_repository"],
            cm_report_repository=deps["cm_report_repository"],
            pm_occurrence_repository=deps["pm_occurrence_repository"],
            pm_schedule_repository=deps["pm_schedule_repository"],
            seal_pump_compatibility_gateway=deps["seal_pump_compatibility_gateway"],
            seal_gateway=deps["seal_gateway"],
            mechanical_seal_stock_repository=deps["mechanical_seal_stock_repository"],
            work_order_gateway=deps.get("work_order_gateway"),
            maintenance_history_gateway=deps.get("maintenance_history_gateway"),
            scope=scope,
        )
    except Exception:
        return None


def _fleet_analytics_unavailable_answer(language: str) -> CopilotAnswer:
    if language == "id":
        return CopilotAnswer("Data fleet analytics sedang tidak tersedia.", DATA_GAP, ())
    return CopilotAnswer("Fleet analytics data is currently unavailable.", DATA_GAP, ())


_HISTORICAL_LEAK_FREQUENCY_WORDS = ("sering", "frequent", "most often", "paling banyak")


def _dispatch_fleet_condition_monitoring(
    question: str,
    scope: frozenset[str] | None,
    *,
    condition_monitoring_reading_gateway,
    pump_gateway,
    language: str = "en",
    **batch_deps: Any,
) -> CopilotAnswer:
    """Fleet-wide (no tag) condition_monitoring intent, split into the
    genuinely distinct query shapes Phase 4/6/7/8 each define -- "highest
    temperature/vibration" (rank_by_parameter), "leaking now" (Phase 7,
    current_leak_pumps), and "leaks most often" (Phase 8,
    historical_leak_frequency) are three different questions the OLD,
    single _handle_leak_frequency_fleet path answered identically (one
    all-time top-1 pump, regardless of which was actually asked).
    Falls back to that pre-existing handler, unchanged, whenever the new
    batch dependencies are not wired for this caller (see
    _build_fleet_batch_or_none) -- never a regression for an existing
    caller/test that only supplies ask_copilot()'s pre-existing params."""
    q = (question or "").lower()

    def has(*words: str) -> bool:
        return any(word in q for word in words)

    is_leak_wording = has("bocor", "leak")
    search_term = None if is_leak_wording else detect_parameter_search_term(question)

    if search_term is not None:
        batch = _build_fleet_batch_or_none(scope, pump_gateway=pump_gateway, **batch_deps)
        if batch is None:
            return _fleet_analytics_unavailable_answer(language)
        return _handle_fleet_parameter_ranking(batch, search_term, language=language)

    if is_leak_wording:
        batch = _build_fleet_batch_or_none(scope, pump_gateway=pump_gateway, **batch_deps)
        if batch is not None:
            if has(*_HISTORICAL_LEAK_FREQUENCY_WORDS):
                period = (
                    parse_condition_monitoring_period(question)
                    or parse_condition_monitoring_period("setahun terakhir")
                )
                return _handle_fleet_historical_leak_frequency(batch, period, language=language)
            return _handle_fleet_current_leak(batch, language=language)
        # Batch dependencies not wired for this caller -- preserve the
        # exact pre-existing all-time-frequency behavior for this
        # question rather than a new DATA_GAP.

    return _handle_leak_frequency_fleet(
        scope, condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        pump_gateway=pump_gateway, language=language,
    )


def _handle_fleet_parameter_ranking(
    batch: "fas.FleetDataBatch", search_term: str, *, language: str = "en"
) -> CopilotAnswer:
    """Phase 4/5/6 -- generic fleet-wide parameter ranking (temperature,
    vibration, pressure, ...), each pump's OWN latest CMON event only
    (fas.rank_by_parameter's own "latest comparable measurement" rule,
    never an all-time maximum). Renders the raw value/unit/measurement-
    point/reading-date as FACT -- never a HIGH/ABNORMAL/CRITICAL label
    (Phase 5: no canonical threshold/baseline source exists for this to
    be an INTERPRETATION)."""
    ranked, evaluated, with_data = fas.rank_by_parameter(batch, search_term, limit=fas.DEFAULT_RANKING_LIMIT)
    label = parameter_display_label(search_term)
    if not ranked:
        if language == "id":
            return CopilotAnswer(
                f"Belum ada data {label} yang tercatat pada fleet ({evaluated} pompa dievaluasi).", DATA_GAP, ()
            )
        return CopilotAnswer(
            f"No {label} data recorded across the fleet ({evaluated} pump(s) evaluated).", DATA_GAP, ()
        )

    lines = [
        f"{i}. {row.equipment_tag} — {row.label}: {row.value} {row.unit} (Reading: {row.reading_date})"
        for i, row in enumerate(ranked, start=1)
    ]
    if language == "id":
        answer = (
            f"Pompa dengan {label} tertinggi:\n" + "\n".join(lines)
            + f"\n\nDievaluasi: {evaluated} pompa / Dengan data {label}: {with_data}"
        )
    else:
        answer = (
            f"Pumps with the highest {label}:\n" + "\n".join(lines)
            + f"\n\nEvaluated: {evaluated} pump(s) / With {label} data: {with_data}"
        )

    evidence = tuple(
        _evidence("ConditionMonitoringReadingRepository", row.equipment_tag, row.label, row.value) for row in ranked
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_fleet_current_leak(batch: "fas.FleetDataBatch", *, language: str = "en") -> CopilotAnswer:
    """Phase 7 -- CURRENT/ACTIVE/LATEST leak evidence only, reusing the
    SAME 30-day active-monitoring window RecommendationEngine's own
    REC_ACTIVE_LEAK rule already uses (fas.current_leak_pumps) -- never a
    second, conflicting definition of "current", and never historical
    frequency."""
    rows = fas.current_leak_pumps(batch)
    if not rows:
        if language == "id":
            return CopilotAnswer("Tidak ada pompa dengan indikasi kebocoran mechanical seal saat ini.", FACT, ())
        return CopilotAnswer("No pump currently shows mechanical seal leak evidence.", FACT, ())

    display = rows[: fas.DEFAULT_RANKING_LIMIT]
    if language == "id":
        lines = [
            f"- {row.equipment_tag} — {row.reading_date}: {row.finding or 'tidak ada catatan temuan'} "
            f"(Status: {row.workflow_status or 'N/A'})"
            for row in display
        ]
        answer = f"{len(rows)} pompa dengan indikasi kebocoran mechanical seal saat ini:\n" + "\n".join(lines)
        if len(rows) > len(display):
            answer += f"\n\nMasih ada {len(rows) - len(display)} pompa lain."
    else:
        lines = [
            f"- {row.equipment_tag} — {row.reading_date}: {row.finding or 'no finding recorded'} "
            f"(Status: {row.workflow_status or 'N/A'})"
            for row in display
        ]
        answer = f"{len(rows)} pump(s) currently show mechanical seal leak evidence:\n" + "\n".join(lines)
        if len(rows) > len(display):
            answer += f"\n\n{len(rows) - len(display)} more pump(s) also affected."

    evidence = tuple(
        _evidence("ConditionMonitoringReadingRepository", row.equipment_tag, "finding", row.finding) for row in display
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_fleet_historical_leak_frequency(batch: "fas.FleetDataBatch", period, *, language: str = "en") -> CopilotAnswer:
    """Phase 8 -- historical leak-event COUNT strictly within `period`,
    never an all-time count and never a substitute for the current-leak
    query above (fas.historical_leak_frequency)."""
    ranked, matching = fas.historical_leak_frequency(batch, period, limit=fas.DEFAULT_RANKING_LIMIT)
    period_label = period.label_id if language == "id" else period.label_en
    if not ranked:
        if language == "id":
            return CopilotAnswer(
                f"Tidak ada kebocoran mechanical seal yang tercatat pada periode {period_label}.", DATA_GAP, ()
            )
        return CopilotAnswer(f"No mechanical seal leak recorded in the period {period_label}.", DATA_GAP, ())

    if language == "id":
        lines = [f"{i}. {row.equipment_tag} — {row.count} kejadian kebocoran" for i, row in enumerate(ranked, start=1)]
        answer = f"Pompa yang paling sering bocor ({period_label}):\n" + "\n".join(lines)
    else:
        lines = [f"{i}. {row.equipment_tag} — {row.count} leak event(s)" for i, row in enumerate(ranked, start=1)]
        answer = f"Pumps that leaked most often ({period_label}):\n" + "\n".join(lines)

    evidence = tuple(
        _evidence("ConditionMonitoringReadingRepository", row.equipment_tag, "leak_event_count", row.count)
        for row in ranked
    )
    return CopilotAnswer(answer, FACT, evidence)


def _detect_fleet_stock_semantic(question: str) -> str | None:
    """Phase 9/10/11 -- ONLY the specific phrasings that need the
    explicit, never-collapsed ZERO_STOCK/NO_STOCK_RECORD/NO_COMPATIBLE_
    SEAL states (fas.classify_fleet_stock): an explicit "record"/
    "catatan" wording, an explicit zero quantity, or "spare seal"
    negated. Every other fleet-stock phrasing (the pre-existing "ga ada
    stocknya"/"tidak ada stock"/"kosong"/"unknown"/"lowest" wording
    _handle_fleet_stock_status already answers) intentionally returns
    None here, unchanged -- see _detect_fleet_stock_semantic's own
    caller for why."""
    q = (question or "").lower()

    def has(*words: str) -> bool:
        return any(word in q for word in words)

    if has("record", "catatan"):
        return "NO_STOCK_RECORD_ONLY"
    if re.search(r"\b(?:stok|stock)[a-z\s]{0,20}\b0\b", q) or has(
        "stok 0", "stock 0", "stok nol", "stock nol", "quantity 0", "qty 0"
    ):
        return "ZERO_STOCK_ONLY"
    if has("tidak ada stock seal", "tidak ada stok seal", "ga ada stock seal", "gak ada stock seal"):
        return "NO_SPARE_BROAD"
    if has("spare seal", "spare part") and has(
        "tidak punya", "tidak ada", "belum punya", "gak punya", "ga punya", "don't have", "doesn't have", "no spare"
    ):
        return "NO_SPARE_BROAD"
    return None


def _render_stock_semantic_rows(matches: list, label_id: str, label_en: str, language: str) -> CopilotAnswer:
    if not matches:
        if language == "id":
            return CopilotAnswer(f"Tidak ada pompa yang {label_id}.", DATA_GAP, ())
        return CopilotAnswer(f"No pumps found that have {label_en}.", DATA_GAP, ())
    if language == "id":
        lines = [f"- {r.equipment_tag} — {r.seal_code or 'N/A'}" for r in matches]
        answer = f"{len(matches)} pompa yang {label_id}:\n" + "\n".join(lines)
    else:
        lines = [f"- {r.equipment_tag} — {r.seal_code or 'N/A'}" for r in matches]
        answer = f"{len(matches)} pump(s) have {label_en}:\n" + "\n".join(lines)
    evidence = tuple(_evidence("FleetAnalyticsStockClassification", r.equipment_tag, "state", r.state) for r in matches)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_fleet_stock_semantics(
    semantic: str, scope: frozenset[str] | None, *, pump_gateway, language: str = "en", **batch_deps: Any
) -> CopilotAnswer:
    """Phase 9/10/11 -- explicit, never-collapsed inventory states via
    fas.classify_fleet_stock(): ZERO_STOCK/NO_STOCK_RECORD/NO_COMPATIBLE_
    SEAL, one row per (equipment, compatible seal) pair, never one
    generic "out of stock" bucket."""
    batch = _build_fleet_batch_or_none(scope, pump_gateway=pump_gateway, **batch_deps)
    if batch is None:
        return _fleet_analytics_unavailable_answer(language)

    rows = fas.classify_fleet_stock(batch)
    if semantic == "ZERO_STOCK_ONLY":
        matches = [r for r in rows if r.state == fas.STOCK_ZERO]
        return _render_stock_semantic_rows(matches, "stok seal tercatat 0", "seal stock recorded as 0", language)
    if semantic == "NO_STOCK_RECORD_ONLY":
        matches = [r for r in rows if r.state == fas.STOCK_NO_RECORD]
        return _render_stock_semantic_rows(
            matches, "tidak punya catatan (record) stok seal", "no seal stock record", language
        )

    # NO_SPARE_BROAD -- "tidak punya spare seal": every reason a pump has
    # no usable spare, grouped and labeled SEPARATELY (Phase 10's own
    # explicit "preserve exact reason per equipment" rule) -- never
    # collapsed into one undifferentiated list.
    zero = [r for r in rows if r.state == fas.STOCK_ZERO]
    no_record = [r for r in rows if r.state == fas.STOCK_NO_RECORD]
    no_compat = [r for r in rows if r.state == fas.STOCK_NO_COMPATIBLE_SEAL]
    if not (zero or no_record or no_compat):
        if language == "id":
            return CopilotAnswer("Setiap pompa memiliki spare seal yang tersedia.", FACT, ())
        return CopilotAnswer("Every pump has an available spare seal.", FACT, ())

    if language == "id":
        sections = []
        if zero:
            sections.append("Stock 0:\n" + "\n".join(f"- {r.equipment_tag} ({r.seal_code})" for r in zero))
        if no_record:
            sections.append(
                "Tidak ada record inventory:\n" + "\n".join(f"- {r.equipment_tag} ({r.seal_code})" for r in no_record)
            )
        if no_compat:
            sections.append("Belum ada compatible seal:\n" + "\n".join(f"- {r.equipment_tag}" for r in no_compat))
        answer = "Pompa yang tidak punya spare seal:\n\n" + "\n\n".join(sections)
    else:
        sections = []
        if zero:
            sections.append("Zero stock:\n" + "\n".join(f"- {r.equipment_tag} ({r.seal_code})" for r in zero))
        if no_record:
            sections.append(
                "No inventory record:\n" + "\n".join(f"- {r.equipment_tag} ({r.seal_code})" for r in no_record)
            )
        if no_compat:
            sections.append("No compatible seal mapped:\n" + "\n".join(f"- {r.equipment_tag}" for r in no_compat))
        answer = "Pumps with no spare seal:\n\n" + "\n\n".join(sections)

    evidence = tuple(
        _evidence("FleetAnalyticsStockClassification", r.equipment_tag, "state", r.state)
        for r in (zero + no_record + no_compat)
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_fleet_overdue_pm(
    scope: frozenset[str] | None, *, pump_gateway, language: str = "en", **batch_deps: Any
) -> CopilotAnswer:
    """Phase 12 -- OVERDUE classified ONLY from real pm_schedule.next_due
    evidence (fas.overdue_pm_pumps, the SAME EngineeringContextEngine.
    _compute_pm_status logic PM-due recommendations already use). A pump
    with no schedule row is UNSCHEDULED, never fabricated as overdue."""
    batch = _build_fleet_batch_or_none(scope, pump_gateway=pump_gateway, **batch_deps)
    if batch is None:
        return _fleet_analytics_unavailable_answer(language)

    overdue = fas.overdue_pm_pumps(batch)
    if not overdue:
        if language == "id":
            return CopilotAnswer("Tidak ada pompa dengan PM overdue berdasarkan jadwal kanonik.", FACT, ())
        return CopilotAnswer("No pump is overdue for PM according to canonical scheduling data.", FACT, ())

    display = overdue[: fas.DEFAULT_RANKING_LIMIT]
    if language == "id":
        lines = [f"- {tag} — jatuh tempo: {next_due}" for tag, next_due in display]
        answer = f"{len(overdue)} pompa overdue PM:\n" + "\n".join(lines)
        if len(overdue) > len(display):
            answer += f"\n\nMasih ada {len(overdue) - len(display)} pompa lain."
    else:
        lines = [f"- {tag} — due: {next_due}" for tag, next_due in display]
        answer = f"{len(overdue)} pump(s) overdue for PM:\n" + "\n".join(lines)
        if len(overdue) > len(display):
            answer += f"\n\n{len(overdue) - len(display)} more pump(s) also overdue."

    evidence = tuple(_evidence("PMScheduleRepository", tag, "next_due", next_due) for tag, next_due in display)
    return CopilotAnswer(answer, FACT, evidence)


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
            f"- {row['equipment_tag']} - {row['seal_type'] or 'N/A'} - "
            f"{row['quantity_available'] if row['quantity_available'] is not None else 'tidak diketahui'}"
            for row in matches
        ]
        answer = f"{len(matches)} pompa {label}:\n" + "\n".join(lines)
    else:
        lines = [
            f"- {row['equipment_tag']} - {row['seal_type'] or 'N/A'} - "
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
    # the WhatsApp caller -- "never silently fail" (this MWO's own rule):
    # every path below terminates as either FACT (nothing needs attention),
    # RECOMMENDATION (a ranked list), or DATA_GAP, never an unhandled crash.
    #
    # MWO-LTSA-FLEET-ATTENTION-001 -- rewritten to a concise, operational
    # WhatsApp shape: one row per PUMP (never several rows for the same
    # pump crowding out a different one -- top_risk_pumps, not the older
    # flat top_risks, which may carry >1 entry per pump), capped at
    # FLEET_ATTENTION_MAX_RESULTS, with a truthful "N more pumps" overflow
    # line reusing attention_pump_count (the fleet's own already-computed
    # total, never approximated). FACT vs RECOMMENDATION is kept explicit:
    # the ranked list itself is a RECOMMENDATION (a derived, prioritized
    # action list), while "no pumps need attention" is a FACT (a direct
    # read of canonical data, not a derived judgement).
    try:
        summary = fleet_executive_summary_service.build(scope=scope)
        # getattr fallback: a caller/test double that only ever set
        # top_risks (pre-this-MWO shape) still renders correctly, one row
        # per entry, rather than raising AttributeError.
        top_risk_pumps = getattr(summary, "top_risk_pumps", None)
        if not top_risk_pumps:
            top_risk_pumps = getattr(summary, "top_risks", None) or ()
        if not top_risk_pumps:
            if language == "id":
                return CopilotAnswer("Tidak ada pompa yang saat ini perlu perhatian dalam cakupan otorisasi Anda.", FACT, ())
            return CopilotAnswer("No pumps currently need attention in your authorized scope.", FACT, ())

        attention_pump_count = getattr(summary, "attention_pump_count", None) or len(top_risk_pumps)
        overflow = max(attention_pump_count - len(top_risk_pumps), 0)

        if language == "id":
            lines = ["Pompa yang perlu perhatian hari ini:", ""]
            for index, risk in enumerate(top_risk_pumps, start=1):
                lines.append(f"{index}. {risk.tag_number} - {risk.title}")
                lines.append(f"   {risk.description}")
                lines.append(f"   Tindakan: {risk.action}")
                lines.append("")
            if overflow > 0:
                lines.append(f"Masih ada {overflow} pompa lain yang memerlukan perhatian.")
                lines.append("")
            lines.append("Source: LTSA canonical data")
        else:
            lines = ["Pumps needing attention today:", ""]
            for index, risk in enumerate(top_risk_pumps, start=1):
                lines.append(f"{index}. {risk.tag_number} - {risk.title}")
                lines.append(f"   {risk.description}")
                lines.append(f"   Action: {risk.action}")
                lines.append("")
            if overflow > 0:
                lines.append(f"{overflow} more pump(s) also need attention.")
                lines.append("")
            lines.append("Source: LTSA canonical data")

        answer = "\n".join(lines)
        evidence = tuple(
            _evidence("FleetExecutiveSummaryService", risk.tag_number, "priority", risk.priority) for risk in top_risk_pumps
        )
        return CopilotAnswer(answer, RECOMMENDATION, evidence)
    except Exception:
        if language == "id":
            return CopilotAnswer("Data prioritas fleet sedang tidak tersedia.", DATA_GAP, ())
        return CopilotAnswer("Fleet priority data is currently unavailable.", DATA_GAP, ())


def _format_diagnostic_value(value: Any) -> str:
    if value == DIAGNOSTIC_DATA_GAP:
        return "DATA_GAP"
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        parts = [f"{key}={_format_diagnostic_value(item)}" for key, item in value.items() if item is not None]
        return ", ".join(parts) if parts else "N/A"
    if isinstance(value, (list, tuple)):
        return ", ".join(_format_diagnostic_value(item) for item in value) if value else "N/A"
    return str(value)


def _format_fact_block(title: str, evidence: dict[str, Any]) -> str:
    if evidence.get("status") == DIAGNOSTIC_DATA_GAP:
        return f"- {title}: DATA_GAP"
    rendered = "; ".join(
        f"{key}={_format_diagnostic_value(value)}"
        for key, value in evidence.items()
        if key != "status" and value is not None
    )
    return f"- {title}: {rendered or evidence.get('status') or 'N/A'}"


def _render_seal_leak_diagnostic(diagnosis: SealLeakDiagnosis) -> str:
    lines: list[str] = [
        f"Mechanical Seal Diagnostic - {diagnosis.equipment}",
        "",
        "Status:",
        f"{diagnosis.diagnostic_status} ({diagnosis.confidence})",
        "",
        "Evidence:",
        _format_fact_block("Leak", diagnosis.leak_evidence),
        _format_fact_block("Temperature", diagnosis.temperature_evidence),
        _format_fact_block("Vibration", diagnosis.vibration_evidence),
        _format_fact_block("Operating", diagnosis.operating_evidence),
        _format_fact_block("Maintenance", diagnosis.maintenance_evidence),
        _format_fact_block("Seal identity", diagnosis.seal_evidence),
        "",
        "Probable causes:",
    ]
    if diagnosis.hypotheses:
        for index, hypothesis in enumerate(diagnosis.hypotheses, start=1):
            evidence = "; ".join(hypothesis.supporting_evidence) if hypothesis.supporting_evidence else "INSUFFICIENT_EVIDENCE"
            missing = "; ".join(hypothesis.missing_or_contradicting_evidence)
            suffix = f" Missing/contradicting: {missing}" if missing else ""
            lines.extend([
                f"{index}. {hypothesis.cause} - {hypothesis.confidence}",
                f"   Evidence: {evidence}{suffix}",
            ])
    else:
        lines.append("No leak evidence found; no probable cause is inferred.")

    lines.extend(["", "Recommended checks:"])
    lines.extend(f"- {check}" for check in diagnosis.recommended_checks) if diagnosis.recommended_checks else lines.append("- None from current evidence.")

    lines.extend(["", "Data needed to confirm:"])
    lines.extend(f"- {item}" for item in diagnosis.missing_evidence) if diagnosis.missing_evidence else lines.append("- Physical inspection evidence and verified failure findings.")

    lines.extend(["", "Spare readiness:"])
    if diagnosis.inventory_evidence:
        for row in diagnosis.inventory_evidence:
            code = row.seal_code or "N/A"
            qty = "DATA_GAP" if row.quantity is None else str(row.quantity)
            lines.append(f"- {code}: {row.state}, qty={qty}")
    else:
        lines.append("- DATA_GAP")

    lines.extend(["", "Conclusion:", "Root cause not confirmed."])
    return "\n".join(lines)


def _diagnostic_evidence(diagnosis: SealLeakDiagnosis) -> tuple[dict[str, Any], ...]:
    rows = [
        _evidence("SealLeakDiagnosticService", diagnosis.equipment, "diagnostic_status", diagnosis.diagnostic_status),
        _evidence("SealLeakDiagnosticService", diagnosis.equipment, "confidence", diagnosis.confidence),
        _evidence("ConditionMonitoringReading", diagnosis.equipment, "current_leak_flag", diagnosis.leak_evidence.get("current_leak_flag")),
        _evidence("ConditionMonitoringReading", diagnosis.equipment, "historical_leak_count", diagnosis.leak_evidence.get("historical_leak_count")),
    ]
    latest = diagnosis.leak_evidence.get("latest_leak_finding")
    if isinstance(latest, dict):
        rows.append(_evidence("ConditionMonitoringReading", latest.get("source") or diagnosis.equipment, "finding", latest.get("finding")))
    return tuple(rows)


def _handle_seal_leak_diagnostic(
    tag: str,
    *,
    seal_leak_diagnostic_service=None,
    ltsa_knowledge_service=None,
    equipment_timeline_service=None,
    **_: Any,
) -> CopilotAnswer:
    if seal_leak_diagnostic_service is None:
        from .seal_leak_diagnostic_service import SealLeakDiagnosticService
        seal_leak_diagnostic_service = SealLeakDiagnosticService(
            ltsa_knowledge_service=ltsa_knowledge_service,
            equipment_timeline_service=equipment_timeline_service,
        )
    diagnosis = seal_leak_diagnostic_service.diagnose(tag)
    kind = DATA_GAP if diagnosis.conclusion in ("INSUFFICIENT_EVIDENCE", "NO_LEAK_EVIDENCE") else INTERPRETATION
    return CopilotAnswer(_render_seal_leak_diagnostic(diagnosis), kind, _diagnostic_evidence(diagnosis))


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
    "seal_leak_diagnostic": _handle_seal_leak_diagnostic,
}


__all__ = [
    "CopilotAnswer", "ask_copilot", "TOOL_HANDLERS",
    "FACT", "INTERPRETATION", "RECOMMENDATION", "DATA_GAP",
]

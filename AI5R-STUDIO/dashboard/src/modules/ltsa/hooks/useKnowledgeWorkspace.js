import { useCallback, useEffect, useRef, useState } from "react";
import { createKnowledgeWorkspaceController } from "../controllers/KnowledgeWorkspaceController";
import { mapPMScheduleRecord, mapPMOccurrenceRecord } from "../utils/pmMapping";
import { mapConditionMonitoringReadingRecord } from "../utils/conditionMonitoringMapping";
import { mapWorkOrderRecord } from "../utils/workOrderMapping";

// MWO-LTSA-032A -- useKnowledgeWorkspace: maps the Knowledge API's raw
// response into the EquipmentKnowledge shape the approved Open Design
// defines (knowledge-panel-spec.md §2). No filtering logic, no second API
// call -- every field below is either a direct rename of a real backend
// field or explicitly left undefined/mapped to an empty collection when
// the backend has no data for it (never fabricated).
//
// MWO-LTSA-032A-R1: fetch, cache, refresh, and retry now live in
// KnowledgeWorkspaceController (../controllers/KnowledgeWorkspaceController.js),
// per that mission's architecture. This hook owns React state
// (data/loading/error) plus all field-mapping below, unchanged in
// behavior from the original MWO-LTSA-032A implementation -- mapping was
// deliberately NOT moved into the controller; see the controller
// module's own header comment for why (an out-of-scope, in-progress
// concurrent edit to Recommendation-mapping, MWO-LTSA-032B).
//
// Disclosed gaps, not silently invented:
//  - equipment.healthScore / criticality / confidence: no backend field
//    exists for any of these today.
//  - equipment.condition: derived from summary.cm_summary.overall_condition
//    (NORMAL -> normal, ABNORMAL -> attention, CRITICAL -> critical), the
//    one real signal available, not a fabricated score. Deliberately kept
//    distinct from equipment.assetStatus (MWO-LTSA-ASSET360-UI-PRODUCTION-
//    HARDENING-001): condition is a health/risk ASSESSMENT (derived from
//    condition-monitoring evidence), assetStatus is the pump's own master-
//    data status column (ltsa_pumps.status, e.g. "UNKNOWN") -- collapsing
//    the two into one ambiguous "Status" field silently discarded whichever
//    one didn't win, per production evidence: 212-P-7B has assetStatus
//    "UNKNOWN" and condition "normal" simultaneously; both are real and
//    neither implies the other.
//  - equipment.area/location/pumpType/assetStatus: MWO-LTSA-ASSET360-UI-
//    PRODUCTION-HARDENING-001 -- read from `pump` (the Knowledge API's own
//    "pump" key, router-side passthrough of knowledge.pump, the same
//    canonical pump record already fetched for this response -- no second
//    gateway call, no second fetch), not from summary.asset
//    (EngineeringContextEngine's own narrower shape, which never carried
//    these fields). A field pump doesn't have (e.g. location, frequently
//    null in production) stays undefined, never fabricated.
//  - mechanicalSeal: MWO-LTSA-ASSET360-MECHANICAL-SEAL-WIRING-001 --
//    EngineeringContextEngine._build_seal_summary's "installed_seal always
//    null" disclosure was about THAT summary field specifically, not the
//    only seal-adjacent data this response carries. The Knowledge API's
//    `current_seal` key (router-side, reusing
//    EquipmentTimelineService.build_current_seal() -- the exact same
//    authoritative Seal-Registry-then-Installation-fallback-then-null
//    derivation GET .../lifecycle already relies on) is mapped here
//    instead. No second fetch: current_seal arrives on this same single
//    response. Every field-level fallback stays `?? undefined`, never a
//    guessed value -- a field the backend has no authoritative source for
//    (e.g. model/temperature/pressure limit when no seal_code resolves in
//    the Seal Registry) is already `null` on the backend dataclass and
//    stays undefined here, rendered as "Unavailable" by KnowledgeSeal.jsx.
//  - inventory[].level: the Open Design's InvItem type has no "unknown"
//    case; a null quantity_on_hand is mapped to level="low" here (the
//    least misleading of the three available choices) with qty text
//    itself set to "Unknown" -- flagged in the deliverable report as an
//    Open Design gap, not resolved unilaterally.

const CM_CONDITION_TO_RISK = {
  NORMAL: "normal",
  ABNORMAL: "attention",
  CRITICAL: "critical",
};

// MWO-LTSA-ASSET360-UI-PRODUCTION-HARDENING-001 -- human-readable,
// null-safe, timezone-explicit (UTC, matching the ISO offset the backend
// already sends -- this app has no other established timezone
// convention to defer to) timestamp formatting. A fixed locale ("en-GB")
// is used deliberately, not the runtime's default locale, so rendered
// output is stable across machines/CI and never test-fragile. No shared
// date-formatting utility exists elsewhere in this module to reuse
// (searched: pumpMapping.js's formatDateOnly is a date-only slice, not a
// datetime formatter).
function formatTimestamp(isoString) {
  if (!isoString) return undefined;

  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return undefined;

  const formatted = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(date);

  return `${formatted} UTC`;
}

function mapEquipment(knowledgeData) {
  const asset = knowledgeData?.summary?.asset ?? null;
  const pump = knowledgeData?.pump ?? null;
  const cmCondition = knowledgeData?.summary?.cm_summary?.overall_condition;
  const condition = CM_CONDITION_TO_RISK[cmCondition];

  return {
    tag: asset?.tag_number ?? pump?.tag_number ?? undefined,
    name: asset?.pump_name ?? pump?.name ?? undefined,
    area: pump?.area ?? undefined,
    location: pump?.location ?? undefined,
    pumpType: pump?.pump_type ?? undefined,
    assetStatus: pump?.status ?? undefined,
    healthScore: undefined,
    condition,
    criticality: undefined,
    confidence: undefined,
    aiSummary: undefined,
    lastUpdated: formatTimestamp(knowledgeData?.summary?.metadata?.generated_at),
  };
}

// MWO-LTSA-ASSET360-SEAL-SEMANTICS-001 -- maps the Knowledge API's
// `configured_seal` (router-side: {seal_type, api_plan} read straight off
// knowledge.pump, the same canonical pump record already fetched for this
// response -- no second gateway call, no second fetch). Deliberately kept
// as its own object, never merged into mapMechanicalSeal's currentSeal
// shape: ltsa_pumps.seal_type is broad master data (production evidence:
// 16 different seal_registry T48MP variants exist with different
// shaft_size values), never proof of what is actually installed today.
function mapConfiguredSeal(configuredSeal) {
  return {
    sealType: configuredSeal?.seal_type ?? undefined,
    apiPlan: configuredSeal?.api_plan ?? undefined,
  };
}

// MWO-LTSA-ASSET360-MECHANICAL-SEAL-WIRING-001 -- maps the Knowledge API's
// `current_seal` (dataclasses.asdict(PumpLifecycleCurrentSeal), router-side,
// see useKnowledgeWorkspace.js's own header comment) into KnowledgeSeal.jsx's
// existing prop vocabulary. `type`/`hours`/`mtbf` have no authoritative
// source anywhere in PumpLifecycleCurrentSeal and are left unset rather
// than guessed -- KnowledgeSeal.jsx already renders an unset field as
// "Not recorded", an honest state, not a fabricated one. `apiPlan` moved
// to mapConfiguredSeal above (MWO-LTSA-ASSET360-SEAL-SEMANTICS-001) --
// api_plan is master/design data (ltsa_pumps.api_plan), not something
// PumpLifecycleCurrentSeal ever carried or should carry.
function mapMechanicalSeal(currentSeal) {
  if (!currentSeal) return undefined;

  return {
    code: currentSeal.seal_code ?? undefined,
    name: currentSeal.seal_name ?? undefined,
    manufacturer: currentSeal.manufacturer ?? undefined,
    model: currentSeal.model ?? undefined,
    material: currentSeal.material ?? undefined,
    status: currentSeal.status ?? undefined,
    installedDate: currentSeal.installed_at ?? undefined,
  };
}

function mapTimeline(timeline) {
  return (timeline ?? []).map((event) => ({
    id: event.id,
    kind: (event.event_type ?? "").toLowerCase(),
    title: event.title,
    time: event.occurred_at,
    desc: event.description,
  }));
}

function mapRefItem(record, { idField, nameLabel, metaField, descriptionField }) {
  const meta = record[metaField];
  const description = descriptionField ? record[descriptionField] : undefined;

  return {
    id: record[idField],
    name: `${nameLabel} ${record[idField]}`,
    meta: description ? `${meta ?? ""} — ${description}`.trim() : meta,
  };
}

// MWO-LTSA-034 -- maps LTSAKnowledgeService._build_drawings()'s real
// output shape (CORE-SERVICES/API/ltsa_knowledge_service.py, MWO-LTSA-033):
// {drawing_id, title, document_number, revision, status, file_name,
// uploaded_at}. Previously mapped through the generic mapRefItem with a
// stale idField ("id") that never existed on the real record -- this MWO
// replaces that placeholder mapping with the real field names. file_name
// (the pointer to the binary) is deliberately not mapped through: this
// MWO's scope is metadata only, and the backend's own docstring already
// excludes file_reference for the same reason.
function mapDrawings(drawings) {
  return (drawings ?? []).map((record) => ({
    id: record.drawing_id,
    title: record.title,
    documentNumber: record.document_number,
    revision: record.revision,
    status: record.status,
    uploadedAt: record.uploaded_at,
  }));
}

function mapCompatibleSeals(seal) {
  return (seal ?? []).map((item) => ({
    id: item.seal_code,
    name: item.part_name ?? item.seal_code,
    meta: item.seal_code,
  }));
}

function mapInventory(inventory) {
  return (inventory ?? []).map((item) => {
    const quantity = item.quantity_on_hand;
    const known = quantity != null;

    return {
      id: item.stock_pool_id,
      stockPoolId: item.stock_pool_id,
      name: item.seal_type ?? "Seal type unknown",
      size: item.application_size ?? item.nominal_size ?? null,
      physicalSize: item.physical_stock_size ?? null,
      reference: item.drawing_reference ?? null,
      available: item.quantity_available ?? null,
      qty: known ? String(item.quantity_available ?? quantity) : "Stock quantity unknown",
      status: item.verification_status ?? "UNKNOWN",
      meta: item.stock_location ?? item.drawing_reference ?? "",
    };
  });
}

// MWO-LTSA-032B -- maps RecommendationEngine.recommend()'s real output
// shape (CORE-SERVICES/API/recommendation_engine.py, MWO-LTSA-031F/R1):
// a list of {id, rule_code, priority, category, title, description,
// evidence: [{source, reference, field, value}], confidence, action}.
// Repository archaeology (MWO-LTSA-032B) confirmed RecommendationEngine
// is NOT wired into GET /api/ltsa/pumps/{tag}/knowledge today -- the live
// endpoint always returns `recommendation: null` (LTSAKnowledgeService's
// own disclosed gap, MWO-LTSA-031A). Wiring it in is a backend/router
// change, explicitly out of scope for this frontend-only mission. This
// mapping is a ready, tested extension point for the day a future,
// separately-authorized MWO serializes the engine's tuple output into
// that same key (the same `dataclasses.asdict()` pattern the router
// already uses for `timeline`) -- it is not verified against real wired
// data, and against today's live backend always yields an empty list.
function mapRecommendations(recommendation) {
  if (!Array.isArray(recommendation)) return [];

  return recommendation.map((rec) => ({
    id: rec.id,
    priority: rec.priority,
    category: rec.category,
    title: rec.title,
    description: rec.description,
    confidence: rec.confidence,
    action: rec.action,
    evidence: (rec.evidence ?? []).map((item) => ({
      source: item.source,
      reference: item.reference,
      field: item.field,
      value: item.value,
    })),
  }));
}

// MWO-LTSA-035 -- maps EngineeringInsight's real output shape
// (CORE-SERVICES/API/engineering_insight.py): {root_cause, risk,
// recommended_action, confidence}, deterministically derived backend-side
// from RecommendationEngine + EngineeringContextEngine, no LLM. `null`
// (no recommendations exist yet) maps to `undefined`, matching every
// other disclosed-gap field in this file -- not fabricated as a locked
// placeholder here; KnowledgeAIInsight.jsx owns the locked-vs-real
// rendering decision.
function mapAiInsight(aiInsight) {
  if (!aiInsight) return undefined;

  return {
    rootCause: aiInsight.root_cause,
    // Reuses the same CM_CONDITION_TO_RISK mapping as equipment.risk --
    // one normalization rule for this raw backend vocabulary, not two.
    risk: CM_CONDITION_TO_RISK[aiInsight.risk],
    recommendedAction: aiInsight.recommended_action,
    confidence: aiInsight.confidence,
  };
}

// MWO-LTSA-036F -- maps LTSAKnowledgeService's pm_schedules (MWO-LTSA-036E)
// into ActivePlansPanel's existing prop shape, reusing pmMapping's
// mapPMScheduleRecord verbatim -- the same mapper PM.jsx itself already
// uses, per ActivePlansPanel's own header comment ("pmSchedules are
// already mapped via pmMapping.mapPMScheduleRecord"). No new mapper is
// created for condition_monitoring_schedules -- ActivePlansPanel consumes
// those raw, exactly as it already did before this MWO (its own header
// comment: "conditionMonitoringSchedules are raw API records"). Both
// arrays are additive keys read off the one Knowledge API response
// already fetched by this hook -- no second fetch, per the Chief
// Architect's "One Aggregate -> One API -> One Fetch" directive.
function mapActivePlans(pmSchedules, conditionMonitoringSchedules) {
  return {
    pmSchedules: (pmSchedules ?? []).map(mapPMScheduleRecord),
    conditionMonitoringSchedules: conditionMonitoringSchedules ?? [],
  };
}

function hasMatchingAssetCode(record, tag) {
  if (!tag) return true;
  return record?.asset_code === tag || record?.tag_number === tag || record?.pump_tag_number === tag;
}

function filterForAsset(records, tag) {
  return (records ?? []).filter((record) => hasMatchingAssetCode(record, tag));
}

function mapEquipmentKnowledge(knowledgeData) {
  const equipment = mapEquipment(knowledgeData);
  const tag = equipment.tag ?? knowledgeData?.tag_number;
  const pmRecords = filterForAsset(knowledgeData?.pm, tag);
  const cmRecords = filterForAsset(knowledgeData?.cm, tag);
  const breakdownRecords = filterForAsset(knowledgeData?.breakdown, tag);
  const conditionMonitoringRecords = filterForAsset(knowledgeData?.condition_monitoring_readings, tag);
  const workOrderRecords = filterForAsset(knowledgeData?.work_orders, tag);

  return {
    equipment,
    activePlans: mapActivePlans(
      filterForAsset(knowledgeData?.pm_schedules, tag),
      filterForAsset(knowledgeData?.condition_monitoring_schedules, tag)
    ),
    timeline: mapTimeline(knowledgeData?.timeline),
    mechanicalSeal: mapMechanicalSeal(knowledgeData?.current_seal),
    configuredSeal: mapConfiguredSeal(knowledgeData?.configured_seal),
    compatibleSeals: mapCompatibleSeals(knowledgeData?.seal),
    inventory: mapInventory(knowledgeData?.inventory),
    pmHistory: pmRecords.map((record) =>
      mapRefItem(record, { idField: "pm_occurrence_code", nameLabel: "PM Occurrence", metaField: "occurrence_date" })
    ),
    cmHistory: cmRecords.map((record) =>
      mapRefItem(record, {
        idField: "cm_report_code",
        nameLabel: "CM Report",
        metaField: "created_at",
        descriptionField: "failure_description",
      })
    ),
    breakdownHistory: breakdownRecords.map((record) =>
      mapRefItem(record, {
        idField: "maintenance_record_code",
        nameLabel: "Breakdown",
        metaField: "performed_at",
        descriptionField: "action_taken",
      })
    ),
    drawings: mapDrawings(knowledgeData?.drawings),
    recommendations: mapRecommendations(knowledgeData?.recommendation),
    aiInsights: mapAiInsight(knowledgeData?.ai_insight),
    // MWO-LTSA-ASSET360-CONSOLIDATION-001 -- full-fidelity records (every
    // real column, via the exact same mappers PM.jsx/ConditionMonitoring.jsx
    // already use), NOT the lossy id/name/meta mapRefItem shape above --
    // Asset 360's Condition Monitoring/PM History/Work Orders sections and
    // the Unified History reuse PMOccurrenceDetailPanel/
    // ConditionMonitoringReadingDetailPanel, both of which need the full
    // record (activities, temperatures DE/NDE, leak, finding, source
    // traceability). pmHistory/cmHistory/breakdownHistory above are left
    // untouched for any other existing consumer of this hook. The filtering
    // here is display integrity only; backend authorization remains the
    // canonical scope control.
    pmOccurrences: pmRecords.map(mapPMOccurrenceRecord),
    conditionMonitoringReadings: conditionMonitoringRecords.map(mapConditionMonitoringReadingRecord),
    workOrders: workOrderRecords.map(mapWorkOrderRecord),
  };
}
export function useKnowledgeWorkspace(tag) {
  const controllerRef = useRef(null);
  if (!controllerRef.current) {
    controllerRef.current = createKnowledgeWorkspaceController();
  }

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);

  // Retry: re-run the fetch effect. A failed load() is never cached by
  // the controller, so this naturally re-fetches -- no force flag needed.
  const retry = useCallback(() => setAttempt((current) => current + 1), []);

  // Refresh: drop this tag's cached entry, then re-run the fetch effect --
  // manual reload, per the mission's Refresh requirement (no polling, no
  // websocket).
  const refresh = useCallback(() => {
    controllerRef.current.invalidate(tag);
    setAttempt((current) => current + 1);
  }, [tag]);

  useEffect(() => {
    if (!tag) {
      setData(null);
      setLoading(false);
      setError(null);
      return undefined;
    }

    let active = true;
    setLoading(true);
    setError(null);

    controllerRef.current
      .load(tag)
      .then((knowledgeData) => {
        if (!active) return;
        setData(mapEquipmentKnowledge(knowledgeData));
      })
      .catch((err) => {
        if (!active) return;
        setData(null);
        setError(err?.message ?? "Pump knowledge API unavailable");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [tag, attempt]);

  return { data, loading, error, refetch: retry, retry, refresh };
}

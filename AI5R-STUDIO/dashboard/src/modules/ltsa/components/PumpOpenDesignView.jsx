import { useMemo, useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import { Section, InfoRow, StatusSignal, RailSection, ActionBar, RefGroup } from "./open-design";
import {
  EngineeringAIStatus,
  EngineeringAISummary,
  EngineeringAIProviderInfo,
  EngineeringAIConfidence,
  EngineeringAIRisk,
  EngineeringAIRemainingLife,
  EngineeringAIFindings,
  EngineeringAIEvidence,
  EngineeringAIRecommendation,
  EngineeringAISourceReferences,
} from "./engineering-ai";

/**
 * MWO-LTSA-050 -- Pump Workspace, migrated to the same Open Design
 * information hierarchy as the Mechanical Seal Workspace (SealOpenDesignView.jsx,
 * MWO-LTSA-042A through MWO-LTSA-048). This is a migration, not a redesign.
 *
 * Domain adaptation from Seal's hierarchy (documented, not silent):
 * - No "resolvedAssetCode" concept: a pump IS the LTSA asset directly
 *   (pump.tag is already the canonical asset code, fetched straight from
 *   ltsa_pumps -- there is no intermediate relationship to resolve, unlike
 *   a seal which may or may not be linked to one).
 * - LTSA Coverage is therefore unconditional: every real pump record comes
 *   from GET /api/ltsa/pumps (the canonical LTSA registry), so it is
 *   always "LTSA Covered" -- a structural fact, not fabricated, just
 *   trivially always true for this asset type.
 * - Criticality is REAL data for a pump (pump.criticality: HIGH/MEDIUM/LOW,
 *   already fetched) -- unlike Seal, which never had this field and always
 *   showed "—". This is the "additional engineering information" MWO-050
 *   asked to be integrated: Current Status and the Inspector Rail both
 *   show the real value instead of a placeholder.
 * - No Lifecycle Stepper: Seal's install/in-service/monitor/end-of-life
 *   states have no defined mapping for a pump asset in this data model --
 *   inventing stepper positions would be fabrication, so the Inspector
 *   Rail simply omits this rail-section rather than showing a meaningless
 *   one. Every other rail-section (Health, Criticality, Recommendation,
 *   Recent Activities) is present.
 * - Compatibility shows "Compatible Seals", populated from
 *   pump.spareParts (getPumpSpareParts, already resolved lazily on
 *   selection by Pump.jsx) -- the real, already-wired pump-side view of
 *   the same seal_pump_compatibility-adjacent relationship, from the
 *   opposite direction. No new API.
 * - Related Engineering reuses the exact same getPMSchedules()/
 *   getCMReports()/getWorkOrders() pattern Seal.jsx already uses, filtered
 *   by `item.equipmentTag === pump.tag` directly (no resolution layer
 *   needed, since pump.tag already IS the asset code).
 * - Engineering Recommendation reuses pump.recommendation (a real field,
 *   currently always null per mapPumpRecord) with the exact same
 *   collapse-when-empty pattern Seal's own section uses.
 * - Action Bar gains three action buttons (View History / Create PM /
 *   Create CM) instead of Seal's one -- passed as children into the
 *   shared ActionBar's already-identical .action-bar-actions container.
 *   Documents' "Buka Drawing" link reuses the exact same onOpenDrawing
 *   mechanism Seal's Documents section uses.
 *
 * MWO-LTSA-050B -- LTSA Open Design Kit: Section/InfoRow/StatusSignal/
 * RailSection/ActionBar/RefGroup extracted to components/open-design/
 * (Priority 1 patterns only -- see the archaeology report). RefGroup's
 * own local definition (previously a documented, deliberate byte-for-byte
 * duplicate of SealOpenDesignView.jsx's copy) is gone, replaced by the
 * shared import this file's own MWO-LTSA-050 header comment already
 * anticipated. Every replacement below preserves the exact prior
 * markup/classes/text -- a refactor, not a redesign.
 *
 * Data discipline (never fabricate): identical to SealOpenDesignView.jsx --
 * every field shows real, already-fetched data or an honest empty state.
 *
 * MWO-LTSA-065 -- Pump Workspace Lifecycle Integration. Current
 * Installation/Current Seal/Timeline/Analytics are new sections, and
 * Current Status/Compatibility/Related Engineering are re-pointed, all
 * sourced from ONE prop: `lifecycle` (GET /api/ltsa/pumps/{tag}/lifecycle,
 * mapped by pumpLifecycleMapping.js). This view never fetches, never
 * resolves, never recomputes anything lifecycle already provides -- it
 * only formats already-real values or shows an honest "Not Available"/
 * empty state when a field is null (per this MWO's own "Display lifecycle
 * values only. Do not resolve again." rule).
 *
 * pump.openWO/pump.lastPM/pump.spareParts (the old per-pump-resolved
 * fields Pump.jsx used to merge onto the selected registry row) are no
 * longer read here at all -- Current Status now reads lifecycle.
 * currentState exclusively.
 *
 * MWO-LTSA-070 -- Engineering Navigation: Timeline and Related Engineering
 * items are now clickable via the optional `onOpenEngineeringObject`
 * prop, reused for both (RefGroup's own new optional `item.onClick`,
 * MWO-LTSA-070). Only object types with a real target workspace
 * (INSTALLATION/PM/CM/WORK_ORDER/DRAWING) get a click handler -- see
 * Pump.jsx's own handleOpenEngineeringObject header comment for the full
 * type-to-route mapping and why FAILURE/REPLACEMENT/Documents stay
 * non-clickable.
 *
 * MWO-LTSA-UI-V2-001 -- Open Design Productionization. The former
 * "Compatibility" section ("Compatible Seals") and Related Engineering's
 * "Inventory" entry rendered the exact same lifecycle.relatedEngineering.
 * inventory array under two different titles -- a duplicate, not two
 * facts (found during the Open Design audit). Both are replaced by one
 * "Seal & Inventory" section, driven by the new `sealInventoryGroups` prop
 * (built once in Pump.jsx by sealMapping.js's buildSealInventoryGroups(),
 * never resolved here -- this view still only displays already-computed
 * data). Each group carries the seal's real Type/Size (from the already-
 * existing getSeals() endpoint), its own stock state (quantity_on_hand's
 * honest null/0/>0 distinction, never fabricated), and its FULL compatible-
 * pump list (via getSealCompatibility(), the already-existing inverse-
 * relationship endpoint Seal.jsx already uses) -- compatible-pump COUNT is
 * always that list's length, never quantity_on_hand, so the two can never
 * be conflated. Multiple seal groups render as independent cards, never
 * collapsed into one -- "Compatible", not "Installed", since the backend
 * does not distinguish the two for this array.
 *
 * Also in this MWO: "Pump Engineering Overview" (a byte-for-byte repeat of
 * Identity's own Technical block) and the permanently-empty "Related
 * Condition Monitoring"/"Related Failure Analysis" groups are removed
 * (no data source exists for either, confirmed during the audit -- not a
 * data loss, they never rendered anything). Documents' 5 static "—" rows
 * are replaced by one honest note. Inspector Rail "Recent Activities"
 * now reuses timelineItems (computed below) instead of a permanently
 * hardcoded empty string.
 */

const NOT_AVAILABLE = "Not Available";

function fmtOrNotAvailable(value) {
  return value == null || value === "" ? NOT_AVAILABLE : value;
}

// Last PM / Next PM / Last CM / Last Failure are each a raw, already-real
// record from a different existing domain (pm_occurrence, pm_schedule,
// cm_report, maintenance_history) -- EquipmentTimelineService passes them
// through unchanged (MWO-LTSA-064A), so this reads only the field names
// those domains' own records already use elsewhere in this codebase
// (equipment_timeline_service.py's own event builders), never a guessed
// or invented field.
function describeRecord(record) {
  if (!record) return null;
  const code =
    record.pm_occurrence_code ?? record.pm_schedule_code ?? record.cm_report_code ??
    record.maintenance_record_code ?? record.work_order_code ?? null;
  const date =
    record.performed_at ?? record.occurrence_date ?? record.next_due ??
    record.created_at ?? record.due_date ?? null;
  return [code, date].filter(Boolean).join(" · ") || null;
}

const STATUS_META = {
  RUNNING: { tier: "normal", label: "Running" },
  STANDBY: { tier: "attention", label: "Standby" },
  MAINTENANCE: { tier: "attention", label: "Maintenance" },
  FAULT: { tier: "critical", label: "Fault" },
};

function statusMeta(status) {
  return STATUS_META[status] || { tier: "neutral", label: status || "Unknown" };
}

// MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- compact Timeline row
// summaries, derived entirely from each event's own already-returned
// payload (event.payload is the raw pm_occurrence/condition_monitoring_
// reading record EquipmentTimelineService already attaches -- no new
// fetch). Deliberately NOT every temperature/measurement -- this is a
// glanceable one-line summary; ConditionMonitoringReadingDetailPanel.jsx
// (reached via the row's own onClick) is the full-detail destination.
function summarizePmActivities(payload) {
  const checklist = payload?.checklist_completion;
  if (!checklist || typeof checklist !== "object") {
    return null;
  }
  const done = Object.entries(checklist)
    .filter(([, value]) => value === true)
    .map(([name]) => name);
  return done.length > 0 ? done.join(", ") : null;
}

function summarizePmEvent(payload) {
  const status = payload?.status ?? NOT_AVAILABLE;
  const activities = summarizePmActivities(payload);
  return activities ? `${status} — ${activities}` : status;
}

function summarizeCmonLeak(payload) {
  // Finding text (when present) is the richest evidence -- prefer it over
  // the bare Y/N flags, never both (would just restate the same fact
  // twice). Tri-state, never guessed: an unset DE/NDE flag is "not
  // recorded", never treated as "no leak".
  if (payload?.finding) {
    return payload.finding;
  }
  const leakDe = payload?.mechanical_seal_leak_de;
  const leakNde = payload?.mechanical_seal_leak_nde;
  if (leakDe === true || leakNde === true) {
    return "Leak detected";
  }
  if (leakDe === false || leakNde === false) {
    return "No leak";
  }
  return "Leak status not recorded";
}

function summarizeCmonEvent(payload) {
  const state = payload?.pump_operating_state ?? NOT_AVAILABLE;
  return `${state} — ${summarizeCmonLeak(payload)}`;
}

// "Same Visit" is derived purely from already-returned Timeline data (no
// new fetch, no persisted relationship): a calendar date where at least
// one PM event and at least one INSPECTION (CMON) event both occurred for
// THIS pump (the whole Timeline is already scoped to one asset). PM and
// CMON remain fully separate records either way -- this is a display-only
// grouping cue.
function sharedPmCmonDates(timeline) {
  const pmDates = new Set();
  const inspectionDates = new Set();
  for (const event of timeline) {
    const day = event.occurredAt ? String(event.occurredAt).slice(0, 10) : null;
    if (!day) continue;
    if (event.eventType === "PM") pmDates.add(day);
    if (event.eventType === "INSPECTION") inspectionDates.add(day);
  }
  const shared = new Set();
  for (const day of pmDates) {
    if (inspectionDates.has(day)) shared.add(day);
  }
  return shared;
}

const CRITICALITY_META = {
  HIGH: { tier: "high", label: "High" },
  MEDIUM: { tier: "attention", label: "Medium" },
  LOW: { tier: "normal", label: "Low" },
};

function criticalityMeta(criticality) {
  return CRITICALITY_META[criticality] || { tier: "neutral", label: criticality || "Unknown" };
}

export default function PumpOpenDesignView({
  pump,
  lifecycle,
  lifecycleLoading,
  sealInventoryGroups,
  onOpenDrawing,
  onOpenEngineeringObject,
  onCreatePM,
  onCreateCM,
  onViewHistory,
  aiResponse,
  aiReady,
  aiStatusText,
  aiStatusVariant,
  aiStatusLabel,
}) {
  const [drawer, setDrawer] = useState(null); // null | "drawing"

  const meta = statusMeta(pump.status);
  const critMeta = criticalityMeta(pump.criticality);

  const coverageMeta = {
    tier: "normal",
    label: "LTSA Covered",
    message: "This pump is a registered LTSA asset.",
  };

  const currentState = lifecycle?.currentState ?? null;
  const currentInstallation = currentState?.currentInstallation ?? null;
  const currentSeal = currentState?.currentSeal ?? null;
  const analytics = lifecycle?.analytics ?? null;
  const timeline = lifecycle?.timeline ?? [];
  const relatedEngineering = lifecycle?.relatedEngineering ?? null;
  const lifecycleEmptyReason = lifecycleLoading ? "Loading…" : "No engineering data";

  // MWO-LTSA-070 -- Related Engineering items become clickable, reusing
  // the same onOpenEngineeringObject(eventType, payload) handler Timeline
  // items use below -- each item's own already-real record IS the
  // payload (Related Engineering's PM/CM/Work Order items are the exact
  // pm_schedule/cm_report/work_order records, unlike a Timeline PM
  // event's pm_occurrence payload, so no field translation is needed
  // here). Documents has no navigable target in this MWO's list -- left
  // non-clickable, not guessed.
  //
  // MWO-LTSA-UI-V2-001 -- "Related Condition Monitoring"/"Related Failure
  // Analysis" (previously hardcoded permanent `items: []`, no backing
  // field exists anywhere yet) and "Inventory" (a byte-for-byte duplicate
  // of the new Seal & Inventory section below) are removed: permanently-
  // empty/duplicate presentation must not consume workspace space, per
  // this MWO's own rule -- not fabricated with placeholder content,
  // simply not shown. No function is lost: neither ever rendered
  // anything real.
  const relatedGroups = [
    {
      id: "pm",
      title: "Related PM",
      items: (relatedEngineering?.pmSchedules ?? []).map((pm) => ({
        key: pm.pm_schedule_code,
        name: pm.pm_schedule_code,
        meta: pm.next_due ? `Jatuh tempo ${pm.next_due}` : pm.procedure,
        flagLabel: pm.status,
        onClick: onOpenEngineeringObject ? () => onOpenEngineeringObject("PM", pm) : undefined,
      })),
      emptyReason: lifecycleEmptyReason,
    },
    {
      id: "cm-reports",
      title: "Related CM Reports",
      items: (relatedEngineering?.cmReports ?? []).map((cm) => ({
        key: cm.cm_report_code,
        name: cm.cm_report_code,
        meta: cm.failure_description,
        flagLabel: cm.status,
        onClick: onOpenEngineeringObject ? () => onOpenEngineeringObject("CM", cm) : undefined,
      })),
      emptyReason: lifecycleEmptyReason,
    },
    {
      id: "wo",
      title: "Related Work Orders",
      items: (relatedEngineering?.workOrders ?? []).map((wo) => ({
        key: wo.work_order_code,
        name: wo.work_order_code,
        meta: wo.title,
        flagLabel: wo.status,
        onClick: onOpenEngineeringObject ? () => onOpenEngineeringObject("WORK_ORDER", wo) : undefined,
      })),
      emptyReason: lifecycleEmptyReason,
    },
    {
      id: "drawings",
      title: "Drawings",
      items: (relatedEngineering?.drawings ?? []).map((drawing) => ({
        key: drawing.drawing_id,
        name: drawing.title ?? drawing.drawing_id,
        meta: [drawing.document_number, drawing.revision ? `Rev ${drawing.revision}` : null].filter(Boolean).join(" · ") || null,
        flagLabel: drawing.status,
        onClick: onOpenEngineeringObject ? () => onOpenEngineeringObject("DRAWING", drawing) : undefined,
      })),
      emptyReason: lifecycleEmptyReason,
    },
    {
      id: "documents",
      title: "Documents",
      items: (relatedEngineering?.documents ?? []).map((doc) => ({
        key: doc.document_code,
        name: doc.title ?? doc.document_code,
        meta: doc.document_type,
        flagLabel: doc.status,
      })),
      emptyReason: lifecycleEmptyReason,
    },
  ];

  // MWO-LTSA-070 -- Timeline events become clickable for the types that
  // have a real target workspace (INSTALLATION/PM/CM/WORK_ORDER, per this
  // MWO's own navigable-type list). FAILURE and REPLACEMENT have no
  // target workspace and stay non-clickable, not guessed.
  // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- INSPECTION (Condition
  // Monitoring readings) added: ConditionMonitoringReadingDetailPanel.jsx
  // already exists and Pump.jsx's handleOpenCmonReading already routes to
  // it correctly (condition_monitoring_reading_code, never the shared
  // UNSCHEDULED:: schedule placeholder) -- this was simply never wired.
  const NAVIGABLE_TIMELINE_TYPES = new Set(["INSTALLATION", "PM", "CM", "WORK_ORDER", "INSPECTION"]);
  const sameVisitDates = useMemo(() => sharedPmCmonDates(timeline), [timeline]);
  // MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- clear visual
  // distinction per seal event type (this MWO's own explicit UI rule),
  // reusing the 3 stock-flag variants LTSAOpenDesign.css already defines
  // (ok/pending/low) rather than inventing new CSS. No drill-down wired
  // for these 7 types: no existing Open Design view/dispatcher entry for
  // SEAL_* event types was found in this audit, and this MWO's own "do
  // not invent broad new UI scope" rule means they stay display-only,
  // like FAILURE/REPLACEMENT above, until a future MWO adds one.
  const SEAL_EVENT_FLAG = {
    SEAL_INSTALL: "ok",
    SEAL_REMOVE: "pending",
    SEAL_INSPECTION: "pending",
    SEAL_REPAIR: "pending",
    SEAL_RETURN_TO_STOCK: "ok",
    SEAL_SCRAP: "low",
  };
  const WARRANTY_DECISION_FLAG = { ACCEPTED: "ok", REJECTED: "low", PENDING_EXAMINATION: "pending" };
  const timelineItems = timeline.map((event) => {
    // Never collapsed into one badge (this MWO's own explicit WARRANTY
    // UI rule): the badge shows only decision_status; window_status is
    // plain meta text alongside the date, never a stock-flag value.
    if (event.eventType === "SEAL_WARRANTY") {
      const decision = event.payload?.decisionStatus ?? event.payload?.decision_status;
      const window = event.payload?.windowStatus ?? event.payload?.window_status;
      return {
        key: event.id,
        name: event.title ?? event.id,
        meta: [window, event.occurredAt].filter(Boolean).join(" · "),
        flagLabel: decision,
        flag: WARRANTY_DECISION_FLAG[decision],
        onClick: undefined,
      };
    }
    // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- compact summary
    // (status+activities for PM, operating state+leak/finding for
    // INSPECTION) appended to the existing date meta line, same " · "
    // join convention the SEAL_WARRANTY branch above already uses. "Same
    // Visit" is appended for either type only on a date that genuinely
    // has both a PM and an INSPECTION event for this pump.
    let summary = null;
    if (event.eventType === "PM") summary = summarizePmEvent(event.payload);
    if (event.eventType === "INSPECTION") summary = summarizeCmonEvent(event.payload);

    const day = event.occurredAt ? String(event.occurredAt).slice(0, 10) : null;
    const isSameVisit =
      (event.eventType === "PM" || event.eventType === "INSPECTION") && day && sameVisitDates.has(day);

    return {
      key: event.id,
      name: event.title ?? event.id,
      meta: [event.occurredAt, summary, isSameVisit ? "Same Visit • PM + Condition Monitoring" : null]
        .filter(Boolean)
        .join(" · "),
      flagLabel: event.eventType,
      flag: SEAL_EVENT_FLAG[event.eventType],
      onClick:
        onOpenEngineeringObject && NAVIGABLE_TIMELINE_TYPES.has(event.eventType)
          ? () => onOpenEngineeringObject(event.eventType, event.payload)
          : undefined,
    };
  });

  // MWO-LTSA-UI-V2-001 -- Recent Activities (Inspector Rail): the 3 most
  // recent real timeline events, most-recent-first. Reuses timelineItems
  // above unmodified (no second timeline transformation) -- lifecycle.
  // timeline is already chronological oldest-first (EquipmentTimelineService.
  // build_lifecycle()), so this is a pure slice/reverse, never a re-sort.
  const recentActivityItems = timelineItems.slice(-3).reverse();

  return (
    <div className="ltsa-open-design" data-testid="pump-open-design">
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            <span>LTSA</span>
            <span className="sep">›</span><span>Pump Registry</span>
            <span className="sep">›</span>
            {/* MWO-LTSA-070 -- PUMP/LIFECYCLE navigation target: this pump's
                own tag, matching the exact crumb-link pattern every other
                Open Design view already uses for its own pump reference
                (e.g. DocumentOpenDesignView.jsx's crumb-pump-link). Both
                PUMP and LIFECYCLE resolve to the same real Pump Workspace
                selection -- no separate "Pump Lifecycle" page exists. */}
            {onOpenEngineeringObject ? (
              <button
                type="button"
                className="crumb-link"
                onClick={() => onOpenEngineeringObject("PUMP", pump)}
                data-od-id="crumb-pump-link"
              >
                <b>{pump.tag}</b>
              </button>
            ) : (
              <b>{pump.tag}</b>
            )}
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>{pump.name}</h1>
            <div className="identity-status">
              <StatusSignal tier={meta.tier} label={meta.label} />
              <span className="running-line">
                <span className="dot-sm" />
                {pump.area ? `Located in ${pump.area}` : "Location unknown"}
              </span>
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Identity</div>
              <InfoRow label="Tag" value={pump.tag} valueClassName="mono" />
              <InfoRow label="Manufacturer" value={pump.manufacturer ?? "—"} />
              <InfoRow label="Area" value={pump.area ?? "—"} />
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Technical</div>
              <InfoRow label="Pump Type" value={pump.type ?? "—"} />
              <InfoRow label="API Plan" value={pump.apiPlan ?? "—"} />
              <InfoRow label="Seal" value={pump.seal ?? "—"} />
              <InfoRow label="Location" value={pump.location ?? "—"} />
            </div>
          </section>

          {/* MWO-LTSA-UI-V2-001 -- the old "Pump Engineering Overview"
              section is removed here: every field it showed (Pump Type,
              API Plan, Seal Type, Location) was a byte-for-byte repeat of
              Identity's own "Technical" block above -- a second section
              for the same four already-visible facts, not new information.
              Merged, not lost: nothing below reads pump.type/apiPlan/seal/
              location a second time. */}

          <Section id="seal-inventory-section" title="Seal & Inventory">
            <div style={{ marginTop: "var(--space-3)" }}>
              {sealInventoryGroups && sealInventoryGroups.length > 0 ? (
                sealInventoryGroups.map((group) => (
                  <div className="part-item" key={group.sealCode ?? group.sealName}>
                    <div className="part-row">
                      <span className="part-name">
                        {group.sealName ?? (group.sealCode ? `Seal ${group.sealCode}` : "Seal code unknown")}
                        {group.shaftSize ? ` · ${group.shaftSize}` : ""}
                      </span>
                      <span
                        className={`stock-flag ${
                          group.quantityOnHand == null ? "pending" : group.quantityOnHand > 0 ? "ok" : "low"
                        }`}
                      >
                        {group.stockLabel}
                      </span>
                    </div>
                    <div className="part-meta">
                      {group.sealCode ? `Code ${group.sealCode}` : null}
                      {group.applicationSize ? ` · Application ${group.applicationSize}` : ""}
                      {group.physicalStockSize ? ` · Physical ${group.physicalStockSize}` : ""}
                      {group.drawingReference ? ` · ${group.drawingReference}` : ""}
                      {group.location ? ` · ${group.location}` : ""}
                    </div>
                    <div style={{ marginTop: "var(--space-2)" }}>
                      <InfoRow
                        label="Compatible Pumps"
                        value={group.compatiblePumps.length}
                      />
                      <InfoRow label="Verification" value={group.verificationStatus || NOT_AVAILABLE} />
                      {group.compatiblePumps.length > 0 && (
                        <div className="confidence-label" style={{ marginTop: "var(--space-1)" }}>
                          {group.compatiblePumps.join(", ")}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                // No repeated "Seal & Inventory" label here -- the
                // enclosing <Section title="Seal & Inventory"> eyebrow
                // above already provides it; RefGroup's own empty-row
                // pattern only repeats its title when used standalone
                // (not already inside a titled Section).
                <div className="info-row">
                  <span className="v ref-group-empty">0 · {lifecycleEmptyReason}</span>
                </div>
              )}
            </div>
          </Section>

          {/* MWO-LTSA-065 -- Current Status now reads lifecycle.currentState
              exclusively for Elapsed Service Days/Last PM/Next PM/Last CM/
              Last Failure/Open Work Orders (previously pump.openWO/
              pump.lastPM, each its own per-pump-resolved fetch). Pump
              Health/Criticality/Coverage are unrelated to lifecycle --
              they are the pump's own identity facts from GET
              /api/ltsa/pumps, unchanged. */}
          <Section id="current-status-section" title="Current Status">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Pump Health" value={meta.label} />
              <InfoRow label="Criticality" value={critMeta.label} />
              <InfoRow label="Coverage" value={coverageMeta.label} />
              <InfoRow label="Elapsed Service Days" value={fmtOrNotAvailable(currentState?.elapsedServiceDays)} />
              <InfoRow label="Last PM" value={fmtOrNotAvailable(describeRecord(currentState?.lastPm))} />
              <InfoRow label="Next PM" value={fmtOrNotAvailable(describeRecord(currentState?.nextPm))} />
              <InfoRow label="Last CM" value={fmtOrNotAvailable(describeRecord(currentState?.lastCm))} />
              <InfoRow label="Last Failure" value={fmtOrNotAvailable(describeRecord(currentState?.lastFailure))} />
              <InfoRow label="Open Work Orders" value={currentState ? currentState.openWorkOrders.length : NOT_AVAILABLE} />
            </div>
          </Section>

          {/* MWO-LTSA-065 -- Current Installation/Current Seal: new
              sections, lifecycle.currentState values displayed as-is, per
              this MWO's "Display lifecycle values only. Do not resolve
              again" rule -- Current Seal's own `source` field (seal_registry
              vs installation_report, MWO-LTSA-064A Section 3) is shown
              honestly rather than hidden. */}
          <Section id="current-installation-section" title="Current Installation">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              {currentInstallation ? (
                <>
                  <InfoRow label="Installation Code" value={currentInstallation.installationCode ?? NOT_AVAILABLE} />
                  <InfoRow label="Report No" value={fmtOrNotAvailable(currentInstallation.reportNo)} />
                  <InfoRow label="Report Date" value={fmtOrNotAvailable(currentInstallation.reportDate)} />
                  <InfoRow label="Drawing No" value={fmtOrNotAvailable(currentInstallation.drawingNo)} />
                  <InfoRow label="Source Document" value={fmtOrNotAvailable(currentInstallation.sourceDocumentName)} />
                </>
              ) : (
                <InfoRow label="Installation" value={lifecycleLoading ? "Loading…" : NOT_AVAILABLE} />
              )}
            </div>
          </Section>

          <Section id="current-seal-section" title="Current Seal">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              {currentSeal ? (
                <>
                  <InfoRow label="Seal Code" value={fmtOrNotAvailable(currentSeal.sealCode)} />
                  <InfoRow label="Seal Name" value={fmtOrNotAvailable(currentSeal.sealName)} />
                  <InfoRow label="Manufacturer" value={fmtOrNotAvailable(currentSeal.manufacturer)} />
                  <InfoRow label="Model" value={fmtOrNotAvailable(currentSeal.model)} />
                  <InfoRow label="Shaft Size" value={fmtOrNotAvailable(currentSeal.shaftSize)} />
                  <InfoRow label="Material" value={fmtOrNotAvailable(currentSeal.material)} />
                  <InfoRow label="Temperature Limit" value={fmtOrNotAvailable(currentSeal.temperatureLimit)} />
                  <InfoRow label="Pressure Limit" value={fmtOrNotAvailable(currentSeal.pressureLimit)} />
                  <InfoRow label="Status" value={fmtOrNotAvailable(currentSeal.status)} />
                  <InfoRow label="Source" value={currentSeal.source === "seal_registry" ? "Seal Registry" : "Installation Report"} />
                </>
              ) : (
                <InfoRow label="Current Seal" value={lifecycleLoading ? "Loading…" : NOT_AVAILABLE} />
              )}
            </div>
          </Section>

          <Section id="coverage-section" title="LTSA Coverage">
            <div className="identity-status" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier={coverageMeta.tier} label={coverageMeta.label} />
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{coverageMeta.message}</p>
          </Section>

          <Section id="recommended-replacement-section" title="Engineering Recommendation">
            {pump.recommendation ? (
              <>
                <h2 className="assessment-headline">{pump.recommendation}</h2>
                <div className="assessment-footer">
                  <StatusSignal tier={meta.tier} label={meta.label} />
                </div>
              </>
            ) : (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>No recommendation available.</p>
            )}
          </Section>

          <Section id="engineering-ai-section" title="Engineering AI">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              {aiReady ? (
                <>
                  <EngineeringAIStatus response={aiResponse} />
                  <EngineeringAISummary response={aiResponse} />
                  <EngineeringAIProviderInfo response={aiResponse} />
                  <EngineeringAIConfidence response={aiResponse} />
                  <EngineeringAIRisk response={aiResponse} />
                  <EngineeringAIRemainingLife response={aiResponse} />
                </>
              ) : (
                <>
                  <StatusSignal tier={aiStatusVariant} label={aiStatusLabel} dot={false} />
                  <div style={{ marginTop: "var(--space-2)" }}>
                    <InfoRow label="Reason" value={aiStatusText} />
                  </div>
                </>
              )}
            </div>
          </Section>
          {aiReady && <EngineeringAIFindings response={aiResponse} />}
          {aiReady && <EngineeringAIEvidence response={aiResponse} />}
          {aiReady && <EngineeringAIRecommendation response={aiResponse} />}
          {aiReady && <EngineeringAISourceReferences response={aiResponse} />}

          <Section id="related-engineering-section" title="Related Engineering">
            <div style={{ marginTop: "var(--space-3)" }}>
              {relatedGroups.map((g) => (
                <RefGroup key={g.id} title={g.title} items={g.items} emptyReason={g.emptyReason} />
              ))}
            </div>
          </Section>

          {/* MWO-LTSA-065 -- Timeline: lifecycle.timeline rendered
              directly, no client-side re-sorting or re-filtering
              (EquipmentTimelineService.build_lifecycle() already returns
              it chronological, oldest first). Supported categories per
              this MWO: INSTALLATION/PM/CM/FAILURE/WORK_ORDER/REPLACEMENT --
              all 6 already flow through event.eventType unchanged, since
              build_lifecycle() only ever populates those 6 (the other 5
              canonical TimelineCategory values have no data source yet,
              per equipment_timeline_service.py's own header comment, and
              build_lifecycle() doesn't call those builders). */}
          <Section id="timeline-section" title="Timeline">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Lifecycle Events" items={timelineItems} emptyReason={lifecycleEmptyReason} />
            </div>
          </Section>

          {/* MWO-LTSA-065 -- Analytics: lifecycle.analytics displayed as-is.
              mtbf/mtbr/averageSealLife/healthIndex/availability/reliability
              are real, currently-always-null placeholders (MWO-LTSA-064A
              Section 5) -- "Not Available" is the honest rendering of
              null, never a computed/fabricated number. */}
          <Section id="analytics-section" title="Analytics">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Elapsed Service Days" value={fmtOrNotAvailable(analytics?.elapsedServiceDays)} />
              <InfoRow label="PM Count" value={fmtOrNotAvailable(analytics?.pmCount)} />
              <InfoRow label="CM Count" value={fmtOrNotAvailable(analytics?.cmCount)} />
              <InfoRow label="Failure Count" value={fmtOrNotAvailable(analytics?.failureCount)} />
              <InfoRow label="MTBF" value={fmtOrNotAvailable(analytics?.mtbf)} />
              <InfoRow label="MTBR" value={fmtOrNotAvailable(analytics?.mtbr)} />
              <InfoRow label="Average Seal Life" value={fmtOrNotAvailable(analytics?.averageSealLife)} />
              <InfoRow label="Health Index" value={fmtOrNotAvailable(analytics?.healthIndex)} />
              <InfoRow label="Availability" value={fmtOrNotAvailable(analytics?.availability)} />
              <InfoRow label="Reliability" value={fmtOrNotAvailable(analytics?.reliability)} />
            </div>
          </Section>

          {/* Documents deliberately keeps raw markup -- same reason as
              SealOpenDesignView.jsx's own Documents section: its eyebrow
              sits inside .section-head alongside a button, deviating from
              the generic Section shape. */}
          {/* MWO-LTSA-UI-V2-001 -- the 5 static "—" Document Type rows are
              removed: none is backed by any field anywhere (confirmed
              during the Open Design audit), so they only ever showed
              fabricated-looking placeholder content. The one real action
              (Buka Drawing) stays; a single honest note replaces the dead
              rows rather than fabricating document types that don't
              exist. */}
          <section className="assessment-section" data-od-id="documents-section">
            <div className="section-head">
              <span className="eyebrow">Documents</span>
              <button
                type="button"
                className="btn-link"
                onClick={() => { onOpenDrawing?.(); setDrawer("drawing"); }}
                data-od-id="open-drawing-link"
              >
                Buka Drawing →
              </button>
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>
              No document types available yet.
            </p>
          </section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="pump-health-section" title="Pump Health">
            <StatusSignal tier={meta.tier} label={meta.label} />
          </RailSection>

          <RailSection id="criticality-section" title="Criticality">
            <StatusSignal tier={critMeta.tier} label={critMeta.label} />
          </RailSection>

          <RailSection id="recommendation-section" title="Recommendation">
            <div className="confidence-label">{pump.recommendation || "No recommendation available."}</div>
          </RailSection>

          {/* MWO-LTSA-UI-V2-001 -- Recent Activities reuses timelineItems
              (already computed above from the real lifecycle.timeline, no
              second transformation engine) instead of a permanently
              hardcoded "no activity" string -- shows the 3 most recent
              real events, most-recent-first. Falls back to an honest empty
              state only when the timeline genuinely has none. */}
          <RailSection id="recent-activities-section" title="Recent Activities">
            {recentActivityItems.length === 0 ? (
              <div className="confidence-label ref-group-empty">
                {lifecycleLoading ? "Loading…" : "No recent activity available."}
              </div>
            ) : (
              recentActivityItems.map((item) => (
                <div className="part-item" key={item.key}>
                  <div className="part-row">
                    <span className="part-name">{item.name}</span>
                    {item.flagLabel && <span className="stock-flag ok">{item.flagLabel}</span>}
                  </div>
                  {item.meta && <div className="part-meta">{item.meta}</div>}
                </div>
              ))
            )}
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={`${pump.tag} · ${meta.label}`}
        metaPrimary={coverageMeta.label}
        metaLabel="Criticality"
        metaValue={critMeta.label}
      >
        <button type="button" className="btn-link" onClick={onViewHistory} data-od-id="action-bar-view-history">
          View History →
        </button>
        <button type="button" className="btn-link" onClick={onCreateCM} data-od-id="action-bar-create-cm">
          Create CM
        </button>
        <button type="button" className="btn-primary" onClick={onCreatePM} data-od-id="action-bar-create-pm">
          Create PM
        </button>
      </ActionBar>

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="Pump Drawing">
        <div className="drawing-thumb" />
        <p>No drawing data available. Drawing Workspace does not yet have a backend.</p>
      </PumpWorkspaceDrawer>
    </div>
  );
}

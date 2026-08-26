import { useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import { Section, InfoRow, StatusSignal, RailSection, ActionBar, RefGroup } from "./open-design";

/**
 * MWO-LTSA-053 -- PM Workspace, migrated to the same LTSA Open Design
 * information hierarchy as Pump (PumpOpenDesignView.jsx) and Mechanical
 * Seal (SealOpenDesignView.jsx). Built entirely from the shared
 * components/open-design/ Kit (Section/InfoRow/StatusSignal/RailSection/
 * ActionBar/RefGroup, MWO-LTSA-050B) and PumpWorkspaceDrawer -- no new
 * design language, no new CSS (every class used here is one
 * LTSAOpenDesign.css already defines).
 *
 * Domain adaptation from Pump/Seal's hierarchy (documented, not silent):
 * - Like Pump (and unlike Seal), pm.equipmentTag IS the real asset code
 *   directly (pmMapping.js: equipmentTag <- asset_code) -- no
 *   resolvedAssetCode indirection needed.
 * - LTSA Coverage is CONDITIONAL, like Seal's (not unconditional like
 *   Pump's): pm.area is only resolved (withResolvedArea, pmMapping.js)
 *   when the equipment_tag successfully looks up via the existing Pump
 *   API. `pm.area !== null` is therefore the same kind of real, already-
 *   computed "is this actually LTSA-covered" signal Seal's
 *   resolvedAssetCode is -- not a fabricated derivation.
 * - Engineering Recommendation reuses pm.recommendation, a real field
 *   (MWO-LTSA-053, pmMapping.js) that is currently always null -- pm_schedule
 *   has no recommendation column yet, same "Derived, not fabricated"
 *   discipline Pump/Seal's own recommendation field already documents.
 * - Engineering AI is a disclosed placeholder ONLY -- per this MWO's
 *   explicit "AI: Placeholder only. No generated recommendation" rule, no
 *   postEngineeringAI call is made for PM at all (unlike Pump/Seal, which
 *   actively call it). The section reuses the exact same aiReady-false
 *   branch markup/classes Pump/Seal's own "not ready" state already uses,
 *   just permanently in that state -- not a new visual pattern.
 * - Checklist Items is real, already-shown data (the old PMDetailPanel.jsx's
 *   own "Checklist" card, pm.checklist) with no dedicated slot in this
 *   MWO's Information Hierarchy -- placed as a third RefGroup inside
 *   Engineering Overview (reusing RefGroup's existing "list of named
 *   items" shape) rather than either inventing a new top-level section or
 *   silently dropping real, currently-visible data.
 * - Recent Activities (Inspector Rail) renders pm.timeline -- real,
 *   already-shown data (the old PMDetailPanel.jsx's own "PM Schedule
 *   Timeline"), currently always [] for the same "not yet derivable"
 *   reason pmMapping.js's own header comment documents. The rail section
 *   itself is Pump/Seal's own established pattern; wiring it to the real
 *   (if empty today) field is more honest than hardcoding an empty state
 *   that could never change.
 * - Related Work Orders (and Related PM/CM) intentionally render as
 *   inline reference rows only, no click-to-navigate badge -- the same
 *   trade-off Seal.jsx's own header comment already documents and
 *   approved when it migrated off per-record navigation badges in favor
 *   of the Open Design's RefGroup rows.
 * - Related Engineering mirrors Pump's exact five groups (Related PM /
 *   Related Condition Monitoring / Related Failure Analysis / Related CM
 *   Reports / Related Work Orders). Related PM is derived from the
 *   already-fetched PM schedule list (same equipmentTag, excluding this
 *   record) -- no new fetch. Related CM Reports reuses getCMReports()/
 *   mapCMReportRecord, the same already-wired call Pump.jsx/Seal.jsx use,
 *   filtered client-side by equipmentTag. Related Work Orders reuses
 *   pm.relatedWorkOrders (real field, currently always [] -- WO-PM-003's
 *   derivation was left for a future MWO per ADR-PM-001, pmMapping.js's
 *   own header comment). Related Condition Monitoring/Failure Analysis
 *   have no data source, same as Pump's identical empty groups.
 * - Action Bar exposes one real action, "Create PM Schedule" -- the exact
 *   same handleCreate/CreatePMScheduleModal mechanism PM.jsx's PageHeader
 *   button already uses, just also reachable from the sticky bar (like
 *   Pump's Action Bar re-exposing its own page-level create actions). No
 *   "View History"/"Create CM" equivalent was invented -- PM has no real,
 *   already-wired handler for either in this context.
 *
 * Data discipline (never fabricate): identical to PumpOpenDesignView.jsx/
 * SealOpenDesignView.jsx -- every field shows real, already-fetched data
 * or an honest empty state.
 */

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- owner-approved
// PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED lifecycle (pmMapping.js's own
// computeDisplayStatus). DUE_SOON is removed (superseded, not renamed --
// never part of the owner's approved vocabulary). ON_HOLD remains
// supported: a pre-existing stored value outside this MWO's own 5 states.
const STATUS_META = {
  PLANNED: { tier: "neutral", label: "Planned" },
  ACTIVE: { tier: "normal", label: "Active" },
  OVERDUE: { tier: "critical", label: "Overdue" },
  COMPLETED: { tier: "neutral", label: "Completed" },
  CANCELLED: { tier: "neutral", label: "Cancelled" },
  ON_HOLD: { tier: "neutral", label: "On Hold" },
};

function statusMeta(status) {
  return STATUS_META[status] || { tier: "neutral", label: status || "Unknown" };
}

export default function PMOpenDesignView({
  pm,
  relatedPMRecords = [],
  cmRecords = [],
  onOpenPump,
  onOpenDrawing,
  onCreatePM,
  canDelete = false,
  onDelete,
  canEdit = false,
  onEdit,
}) {
  const [drawer, setDrawer] = useState(null); // null | "drawing"

  const meta = statusMeta(pm.status);
  const covered = pm.area !== null;

  // LTSA Coverage: conditional, like Seal's -- pm.area is only non-null
  // when withResolvedArea's getPump(equipmentTag) call actually resolved
  // a real pump (pmMapping.js), so this is a real, already-computed fact,
  // not a fabricated derivation.
  const coverageMeta = covered
    ? { tier: "normal", label: "LTSA Covered", message: "Linked to an LTSA-covered pump." }
    : {
        tier: "neutral",
        label: "Coverage Unknown",
        message: "This PM schedule's equipment could not be resolved to an LTSA-covered pump.",
      };

  const dataEmptyReason = "No engineering data";

  const overviewGroups = [
    {
      id: "checklist",
      title: "Checklist Items",
      items: pm.checklist.map((item) => ({ key: item, name: item })),
      emptyReason: dataEmptyReason,
    },
  ];

  const relatedGroups = [
    {
      id: "pm",
      title: "Related PM",
      items: relatedPMRecords.map((item) => ({
        key: item.id,
        name: item.id,
        meta: item.nextDue ? `Due ${item.nextDue}` : item.procedure,
        flagLabel: item.status,
      })),
      emptyReason: dataEmptyReason,
    },
    { id: "cm", title: "Related Condition Monitoring", items: [], emptyReason: dataEmptyReason },
    { id: "fa", title: "Related Failure Analysis", items: [], emptyReason: dataEmptyReason },
    {
      id: "cm-reports",
      title: "Related CM Reports",
      items: cmRecords.map((cm) => ({ key: cm.id, name: cm.id, meta: cm.failureDescription, flagLabel: cm.status })),
      emptyReason: dataEmptyReason,
    },
    {
      id: "wo",
      title: "Related Work Orders",
      items: pm.relatedWorkOrders.map((id) => ({ key: id, name: id })),
      emptyReason: dataEmptyReason,
    },
  ];

  return (
    <div className="ltsa-open-design" data-testid="pm-open-design">
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            {pm.equipmentTag ? (
              <button
                type="button"
                className="crumb-link"
                onClick={() => onOpenPump?.(pm.equipmentTag)}
                data-od-id="crumb-pump-link"
              >
                {pm.equipmentTag}
              </button>
            ) : (
              <span>Unknown Asset</span>
            )}
            <span className="sep">›</span><span>Preventive Maintenance</span>
            <span className="sep">›</span><b>{pm.id}</b>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>{pm.procedure}</h1>
            <div className="identity-status">
              <StatusSignal tier={meta.tier} label={meta.label} />
              <span className="running-line">
                <span className="dot-sm" />
                {pm.equipmentTag ? `Asset ${pm.equipmentTag}${pm.area ? ` · ${pm.area}` : ""}` : "Asset unknown"}
              </span>
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Identity</div>
              <InfoRow label="PM Schedule" value={pm.id} valueClassName="mono" />
              <InfoRow label="Equipment" value={pm.equipmentTag ?? "—"} />
              <InfoRow label="Area" value={pm.area ?? "—"} />
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Technical</div>
              <InfoRow label="Frequency" value={pm.frequency ?? "—"} />
              <InfoRow label="Trigger Type" value={pm.triggerType ?? "—"} />
              <InfoRow label="Assigned Technician" value={pm.assignedTechnician ?? "—"} />
            </div>
          </section>

          <Section id="engineering-overview-section" title="PM Engineering Overview">
            <div className="assessment-columns" style={{ marginTop: "var(--space-3)" }}>
              <div>
                <div className="eyebrow">Schedule Classification</div>
                <InfoRow label="Frequency" value={pm.frequency ?? "—"} />
                <InfoRow label="Trigger Type" value={pm.triggerType ?? "—"} />
              </div>
              <div>
                <div className="eyebrow">Assignment</div>
                <InfoRow label="Assigned Technician" value={pm.assignedTechnician ?? "—"} />
                <InfoRow
                  label="Estimated Duration"
                  value={pm.estimatedDurationHours != null ? `${pm.estimatedDurationHours} hrs` : "—"}
                />
              </div>
            </div>
            <div style={{ marginTop: "var(--space-3)" }}>
              {overviewGroups.map((g) => (
                <RefGroup key={g.id} title={g.title} items={g.items} emptyReason={g.emptyReason} />
              ))}
            </div>
          </Section>

          <Section id="current-status-section" title="Current Status">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Status" value={meta.label} />
              <InfoRow label="Next Due" value={pm.nextDue ?? "Unknown"} />
              <InfoRow label="Last Performed" value={pm.lastPerformed ?? "Not yet performed"} />
              <InfoRow label="Coverage" value={coverageMeta.label} />
            </div>
          </Section>
          {/* MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- Edit gated on the same
              MAINTENANCE_WRITE capability the backend PATCH endpoint
              itself requires (PM.jsx's canWriteMaintenance), independent
              of canDelete (SUPERUSER-only). */}
          {(canEdit || canDelete) && (
            <Section id="schedule-actions" title="Schedule Actions">
              <div style={{ display: "flex", gap: "var(--space-2)" }}>
                {canEdit && (
                  <button type="button" className="btn-link" onClick={() => onEdit?.(pm)} data-od-id="edit-schedule">
                    Edit Schedule
                  </button>
                )}
                {canDelete && (
                  <button
                    type="button"
                    onClick={() => {
                      const reason = window.prompt(`Deactivate ${pm.id}:`);
                      if (reason?.trim() && window.confirm(`Deactivate ${pm.id}?`)) onDelete?.(pm.id, reason.trim());
                    }}
                  >
                    Deactivate Schedule
                  </button>
                )}
              </div>
            </Section>
          )}

          <Section id="coverage-section" title="LTSA Coverage">
            <div className="identity-status" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier={coverageMeta.tier} label={coverageMeta.label} />
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{coverageMeta.message}</p>
          </Section>

          <Section id="recommended-replacement-section" title="Engineering Recommendation">
            {pm.recommendation ? (
              <>
                <h2 className="assessment-headline">{pm.recommendation}</h2>
                <div className="assessment-footer">
                  <StatusSignal tier={meta.tier} label={meta.label} />
                </div>
              </>
            ) : (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>No recommendation available.</p>
            )}
          </Section>

          {/* Engineering AI: placeholder only, per this MWO's explicit
              rule -- no postEngineeringAI call is made for PM, so this
              section is permanently in the same "not ready" branch
              Pump/Seal's own aiReady=false state already renders. */}
          <Section id="engineering-ai-section" title="Engineering AI">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier="unavailable" label="Unavailable" dot={false} />
              <div style={{ marginTop: "var(--space-2)" }}>
                <InfoRow label="Reason" value="Engineering AI has not been integrated for PM Schedules yet." />
              </div>
            </div>
          </Section>

          <Section id="related-engineering-section" title="Related Engineering">
            <div style={{ marginTop: "var(--space-3)" }}>
              {relatedGroups.map((g) => (
                <RefGroup key={g.id} title={g.title} items={g.items} emptyReason={g.emptyReason} />
              ))}
            </div>
          </Section>

          {/* Documents deliberately keeps raw markup, matching Pump/Seal's
              own documented exception -- its eyebrow sits inside
              .section-head alongside a button, deviating from Section's
              generic shape. */}
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
            <div style={{ marginTop: "var(--space-2)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Document Types</div>
              <InfoRow label="Drawing" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Datasheet" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Checklist Sheet" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Certificates" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Revision History" value="—" valueClassName="ref-group-empty" />
            </div>
          </section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="pm-status-section" title="PM Status">
            <StatusSignal tier={meta.tier} label={meta.label} />
          </RailSection>

          <RailSection id="recommendation-section" title="Recommendation">
            <div className="confidence-label">{pm.recommendation || "No recommendation available."}</div>
          </RailSection>

          <RailSection id="recent-activities-section" title="Recent Activities">
            {pm.timeline.length === 0 ? (
              <div className="confidence-label ref-group-empty">No recent activity available.</div>
            ) : (
              pm.timeline.map((entry, i) => (
                <div className="confidence-label" key={`${entry.date}-${i}`}>{entry.date} — {entry.event}</div>
              ))
            )}
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={`${pm.id} · ${meta.label}`}
        metaPrimary={coverageMeta.label}
        metaLabel="Next Due"
        metaValue={pm.nextDue ?? "Unknown"}
      >
        {pm.equipmentTag && (
          <button type="button" className="btn-link" onClick={() => onOpenPump?.(pm.equipmentTag)} data-od-id="action-bar-open-pump">
            Buka Pump →
          </button>
        )}
        <button type="button" className="btn-primary" onClick={onCreatePM} data-od-id="action-bar-create-pm">
          Create PM Schedule
        </button>
      </ActionBar>

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="PM Drawing">
        <div className="drawing-thumb" />
        <p>No drawing data available. Drawing Workspace does not yet have a backend.</p>
      </PumpWorkspaceDrawer>
    </div>
  );
}

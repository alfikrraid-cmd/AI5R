import { useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import { Section, InfoRow, StatusSignal, RailSection, ActionBar, RefGroup } from "./open-design";

/**
 * MWO-LTSA-054 -- CM (Corrective Maintenance / Failure Records) Workspace,
 * migrated to the same LTSA Open Design information hierarchy as Pump
 * (PumpOpenDesignView.jsx), Mechanical Seal (SealOpenDesignView.jsx), and
 * PM (PMOpenDesignView.jsx). Built entirely from the shared
 * components/open-design/ Kit and PumpWorkspaceDrawer -- no new design
 * language, no new CSS (every class used here is one LTSAOpenDesign.css
 * already defines).
 *
 * Domain adaptation from Pump/Seal/PM's hierarchy (documented, not silent):
 * - Like PM, cm.equipmentTag IS the real asset code directly (cmMapping.js:
 *   equipmentTag <- asset_code), and LTSA Coverage is CONDITIONAL on
 *   cm.area (only non-null once withResolvedArea's getPump() call actually
 *   resolves a real pump) -- the same real, already-computed signal PM's
 *   own coverageMeta already uses, not a fabricated derivation.
 * - Engineering Recommendation reuses cm.recommendation, a real field
 *   (MWO-LTSA-054, cmMapping.js) that is currently always null --
 *   cm_report has no recommendation column yet, same "Derived, not
 *   fabricated" discipline Pump/Seal/PM's own recommendation field
 *   already documents.
 * - Root Cause & Actions is real, already-populated data (the old
 *   CMDetailPanel.jsx's own "Root Cause & Actions" card: rootCause/
 *   immediateAction/correctiveAction) with no dedicated slot in the
 *   reused Information Hierarchy -- placed as a third InfoRow block
 *   inside Engineering Overview, the same "extra real field, no new
 *   section" treatment PM's own Checklist Items got.
 * - Engineering AI is a disclosed placeholder ONLY, matching PM's exact
 *   precedent (PMOpenDesignView.jsx) -- no postEngineeringAI call is made
 *   for CM. CM.jsx never called it before this migration either; wiring a
 *   live call now would be a new capability, not a reuse of the existing
 *   Open Design.
 * - Related Engineering mirrors Pump/PM's exact five groups. Related PM
 *   reuses getPMSchedules()/mapPMScheduleRecord (the same already-wired
 *   call PM.jsx/Pump.jsx use), filtered client-side by equipmentTag.
 *   Related CM Reports shows sibling reports (same equipmentTag,
 *   excluding this record) from the already-fetched list -- no new
 *   fetch, mirroring PM's own "Related PM" derivation. Related Condition
 *   Monitoring/Failure Analysis have no data source, same as Pump/Seal/
 *   PM's identical empty groups. Related Work Orders shows the one real,
 *   directly-linked cm.relatedWorkOrder (work_order_code) -- a precise,
 *   real relationship, not the "same equipment tag" proxy Pump's own
 *   Related Work Orders group uses, since a CM report already carries a
 *   direct FK to its one work order.
 * - Action Bar exposes one real action, "Create CM Report" -- the exact
 *   same handleCreate/CreateCMReportModal mechanism CM.jsx's PageHeader
 *   button already uses, just also reachable from the sticky bar (same
 *   pattern PM's own Action Bar established).
 *
 * Data discipline (never fabricate): identical to PumpOpenDesignView.jsx/
 * SealOpenDesignView.jsx/PMOpenDesignView.jsx -- every field shows real,
 * already-fetched data or an honest empty state.
 */

const STATUS_META = {
  OPEN: { tier: "critical", label: "Open" },
  IN_PROGRESS: { tier: "attention", label: "In Progress" },
  RESOLVED: { tier: "normal", label: "Resolved" },
  CLOSED: { tier: "neutral", label: "Closed" },
};

function statusMeta(status) {
  return STATUS_META[status] || { tier: "neutral", label: status || "Unknown" };
}

export default function CMOpenDesignView({
  cm,
  relatedPMRecords = [],
  relatedCMRecords = [],
  onOpenPump,
  onOpenDrawing,
  onCreateCM,
}) {
  const [drawer, setDrawer] = useState(null); // null | "drawing"

  const meta = statusMeta(cm.status);
  const covered = cm.area !== null;

  const coverageMeta = covered
    ? { tier: "normal", label: "LTSA Covered", message: "Linked to an LTSA-covered pump." }
    : {
        tier: "neutral",
        label: "Coverage Unknown",
        message: "This report's equipment could not be resolved to an LTSA-covered pump.",
      };

  const dataEmptyReason = "No engineering data";

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
    { id: "cmon", title: "Related Condition Monitoring", items: [], emptyReason: dataEmptyReason },
    { id: "fa", title: "Related Failure Analysis", items: [], emptyReason: dataEmptyReason },
    {
      id: "cm-reports",
      title: "Related CM Reports",
      items: relatedCMRecords.map((item) => ({
        key: item.id,
        name: item.id,
        meta: item.failureDescription,
        flagLabel: item.status,
      })),
      emptyReason: dataEmptyReason,
    },
    {
      id: "wo",
      title: "Related Work Orders",
      items: cm.relatedWorkOrder ? [{ key: cm.relatedWorkOrder, name: cm.relatedWorkOrder }] : [],
      emptyReason: dataEmptyReason,
    },
  ];

  return (
    <div className="ltsa-open-design" data-testid="cm-open-design">
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            {cm.equipmentTag ? (
              <button
                type="button"
                className="crumb-link"
                onClick={() => onOpenPump?.(cm.equipmentTag)}
                data-od-id="crumb-pump-link"
              >
                {cm.equipmentTag}
              </button>
            ) : (
              <span>Unknown Asset</span>
            )}
            <span className="sep">›</span><span>Corrective Maintenance</span>
            <span className="sep">›</span><b>{cm.id}</b>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>{cm.failureDescription}</h1>
            <div className="identity-status">
              <StatusSignal tier={meta.tier} label={meta.label} />
              <span className="running-line">
                <span className="dot-sm" />
                {cm.equipmentTag ? `Asset ${cm.equipmentTag}${cm.area ? ` · ${cm.area}` : ""}` : "Asset unknown"}
              </span>
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Identity</div>
              <InfoRow label="CM Report" value={cm.id} valueClassName="mono" />
              <InfoRow label="Equipment" value={cm.equipmentTag ?? "—"} />
              <InfoRow label="Area" value={cm.area ?? "—"} />
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Technical</div>
              <InfoRow label="Failure Category" value={cm.failureCategory ?? "—"} />
              <InfoRow label="Severity" value={cm.severity ?? "—"} />
              <InfoRow label="Priority" value={cm.priority ?? "—"} />
            </div>
          </section>

          <Section id="engineering-overview-section" title="CM Engineering Overview">
            <div className="assessment-columns" style={{ marginTop: "var(--space-3)" }}>
              <div>
                <div className="eyebrow">Failure Classification</div>
                <InfoRow label="Failure Category" value={cm.failureCategory ?? "—"} />
                <InfoRow label="Severity" value={cm.severity ?? "—"} />
                <InfoRow label="Priority" value={cm.priority ?? "—"} />
              </div>
              <div>
                <div className="eyebrow">Assignment &amp; Impact</div>
                <InfoRow label="Assigned Technician" value={cm.assignedTechnician ?? "—"} />
                <InfoRow label="Downtime" value={cm.downtimeHours != null ? `${cm.downtimeHours} hrs` : "—"} />
              </div>
            </div>
            <div style={{ marginTop: "var(--space-3)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Root Cause &amp; Actions</div>
              <InfoRow label="Root Cause" value={cm.rootCause ?? "—"} />
              <InfoRow label="Immediate Action" value={cm.immediateAction ?? "—"} />
              <InfoRow label="Corrective Action" value={cm.correctiveAction ?? "—"} />
            </div>
          </Section>

          <Section id="current-status-section" title="Current Status">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Status" value={meta.label} />
              <InfoRow label="Downtime" value={cm.downtimeHours != null ? `${cm.downtimeHours} hrs` : "Unknown"} />
              <InfoRow label="Assigned Technician" value={cm.assignedTechnician ?? "Unassigned"} />
              <InfoRow label="Coverage" value={coverageMeta.label} />
            </div>
          </Section>

          <Section id="coverage-section" title="LTSA Coverage">
            <div className="identity-status" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier={coverageMeta.tier} label={coverageMeta.label} />
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{coverageMeta.message}</p>
          </Section>

          <Section id="recommended-replacement-section" title="Engineering Recommendation">
            {cm.recommendation ? (
              <>
                <h2 className="assessment-headline">{cm.recommendation}</h2>
                <div className="assessment-footer">
                  <StatusSignal tier={meta.tier} label={meta.label} />
                </div>
              </>
            ) : (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>No recommendation available.</p>
            )}
          </Section>

          {/* Engineering AI: placeholder only -- no postEngineeringAI call
              is made for CM (matching PMOpenDesignView.jsx's identical
              precedent), permanently in the same "not ready" branch
              Pump/Seal's own aiReady=false state already renders. */}
          <Section id="engineering-ai-section" title="Engineering AI">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier="unavailable" label="Unavailable" dot={false} />
              <div style={{ marginTop: "var(--space-2)" }}>
                <InfoRow label="Reason" value="Engineering AI has not been integrated for CM Reports yet." />
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

          {/* Documents deliberately keeps raw markup, matching Pump/Seal/
              PM's own documented exception. */}
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
              <InfoRow label="Inspection Report" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Certificates" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Revision History" value="—" valueClassName="ref-group-empty" />
            </div>
          </section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="cm-status-section" title="CM Status">
            <StatusSignal tier={meta.tier} label={meta.label} />
          </RailSection>

          <RailSection id="recommendation-section" title="Recommendation">
            <div className="confidence-label">{cm.recommendation || "No recommendation available."}</div>
          </RailSection>

          <RailSection id="recent-activities-section" title="Recent Activities">
            {cm.timeline.length === 0 ? (
              <div className="confidence-label ref-group-empty">No recent activity available.</div>
            ) : (
              cm.timeline.map((entry, i) => (
                <div className="confidence-label" key={`${entry.date}-${i}`}>{entry.date} — {entry.event}</div>
              ))
            )}
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={`${cm.id} · ${meta.label}`}
        metaPrimary={coverageMeta.label}
        metaLabel="Downtime"
        metaValue={cm.downtimeHours != null ? `${cm.downtimeHours} hrs` : "Unknown"}
      >
        {cm.equipmentTag && (
          <button type="button" className="btn-link" onClick={() => onOpenPump?.(cm.equipmentTag)} data-od-id="action-bar-open-pump">
            Buka Pump →
          </button>
        )}
        <button type="button" className="btn-primary" onClick={onCreateCM} data-od-id="action-bar-create-cm">
          Create CM Report
        </button>
      </ActionBar>

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="CM Drawing">
        <div className="drawing-thumb" />
        <p>No drawing data available. Drawing Workspace does not yet have a backend.</p>
      </PumpWorkspaceDrawer>
    </div>
  );
}

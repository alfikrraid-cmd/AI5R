import { useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import AssetIdentityHeader, { HealthCard } from "./AssetIdentityHeader";
import WorkspaceTabStrip from "./WorkspaceTabStrip";
import { IconCheck } from "./PumpWorkspaceIcons";
import { Section, InfoRow, StatusSignal, RefGroup } from "./open-design";

/**
 * UI-D2B -- Preventive Maintenance Workspace, migrated from the pre-
 * UI-D1.2 Open Design hierarchy (ChromeBar/crumb + workspace-grid/
 * object-column/inspector-rail + sticky Action Bar -- MWO-LTSA-053's
 * original shape) to Chief's approved reference: AssetIdentityHeader +
 * WorkspaceTabStrip + tabbed sections, the same shared components
 * PumpOpenDesignView.jsx/SealOpenDesignView.jsx/WorkOrderOpenDesignView.jsx
 * already use. This is a migration, not a redesign of the underlying
 * domain data or behavior -- every field/section below is the same real,
 * already-fetched value the old hierarchy rendered, just regrouped into
 * tabs:
 * - Overview: old Identity/Hero + "PM Engineering Overview" + "Current
 *   Status" + "LTSA Coverage" sections, Checklist Items, and Schedule
 *   Actions (Edit/Deactivate), plus a new Quick Actions card mirroring
 *   Pump/Work Order's own Overview Quick Actions card.
 * - Engineering AI: old "Engineering AI" section, unchanged -- still a
 *   disclosed placeholder only (no postEngineeringAI call exists for PM,
 *   per this domain's own explicit "AI: Placeholder only" rule; not
 *   invented here).
 * - Documents: old raw-markup Documents section, unchanged.
 * - History: old "Recent Activities" (Inspector Rail) + "Related
 *   Engineering" + "Engineering Recommendation", combined onto one tab.
 *
 * Data discipline (unchanged): every field shows real, already-fetched
 * data or an honest empty state -- never fabricated.
 */

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

const PM_TABS = [
  { key: "overview", label: "Overview" },
  { key: "engineering-ai", label: "Engineering AI" },
  { key: "documents", label: "Documents" },
  { key: "history", label: "History" },
];

export default function PMOpenDesignView({
  pm,
  relatedPMRecords = [],
  cmRecords = [],
  onOpenPump,
  onOpenDrawing,
  onCreatePM,
  onBack,
  canDelete = false,
  onDelete,
  canEdit = false,
  onEdit,
}) {
  const [drawer, setDrawer] = useState(null); // null | "drawing"
  const [activeTab, setActiveTab] = useState("overview");

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

  const checklistGroup = {
    id: "checklist",
    title: "Checklist Items",
    items: pm.checklist.map((item) => ({ key: item, name: item })),
    emptyReason: dataEmptyReason,
  };

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
      // UI-D2B -- canonical terminology rule (this mission, section 11):
      // "CM" in new UI/code means Condition Monitoring, never Corrective
      // Maintenance, going forward. This group's real data source
      // (cmRecords/getCMReports/cm_report) is the legacy Corrective
      // Maintenance domain (proven in UI-D2A.1's own terminology audit),
      // so its title is spelled out in full here rather than abbreviated
      // "CM Reports" -- the legacy data/route/table itself is untouched.
      id: "cm-reports",
      title: "Related Corrective Maintenance Reports",
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
      <AssetIdentityHeader
        icon={<IconCheck />}
        tag={pm.id}
        name={pm.procedure}
        subtitle={pm.equipmentTag ? `Asset ${pm.equipmentTag}${pm.area ? ` · ${pm.area}` : ""}` : "Asset unknown"}
        onBack={onBack}
      >
        <HealthCard label="Status" value={meta.label} tone={meta.tier} />
        <HealthCard label="Frequency" value={pm.frequency ?? "N/A"} />
      </AssetIdentityHeader>

      <WorkspaceTabStrip items={PM_TABS} activeKey={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" && (
        <div className="workspace-overview-grid">
          <div className="workspace-overview-card" data-od-id="identity-section">
            <div className="eyebrow">Asset Information</div>
            <InfoRow label="PM Schedule" value={pm.id} valueClassName="mono" />
            <InfoRow label="Equipment" value={pm.equipmentTag ?? "N/A"} />
            <InfoRow label="Area" value={pm.area ?? "N/A"} />
            <InfoRow label="Next Due" value={pm.nextDue ?? "N/A"} />
            <InfoRow label="Last Performed" value={pm.lastPerformed ?? "Not yet performed"} />
          </div>

          <div className="workspace-overview-card">
            <div className="eyebrow">Schedule &amp; Assignment</div>
            <InfoRow label="Frequency" value={pm.frequency ?? "N/A"} />
            <InfoRow label="Trigger Type" value={pm.triggerType ?? "N/A"} />
            <InfoRow label="Assigned Technician" value={pm.assignedTechnician ?? "N/A"} />
            <InfoRow
              label="Estimated Duration"
              value={pm.estimatedDurationHours != null ? `${pm.estimatedDurationHours} hrs` : "N/A"}
            />
            <InfoRow label="Status" value={meta.label} />
          </div>

          <div className="workspace-overview-card">
            <div className="eyebrow">Quick Actions</div>
            <div className="workspace-quick-actions">
              {pm.equipmentTag && (
                <button type="button" className="workspace-quick-action-btn" onClick={() => onOpenPump?.(pm.equipmentTag)} data-od-id="action-bar-open-pump">
                  Buka Pump →
                </button>
              )}
              {canEdit && (
                <button type="button" className="workspace-quick-action-btn" onClick={() => onEdit?.(pm)} data-od-id="edit-schedule">
                  Edit Schedule
                </button>
              )}
              {canDelete && (
                <button
                  type="button"
                  className="workspace-quick-action-btn"
                  onClick={() => {
                    const reason = window.prompt(`Deactivate ${pm.id}:`);
                    if (reason?.trim() && window.confirm(`Deactivate ${pm.id}?`)) onDelete?.(pm.id, reason.trim());
                  }}
                >
                  Deactivate Schedule
                </button>
              )}
              <button type="button" className="workspace-quick-action-btn" onClick={onCreatePM} data-od-id="action-bar-create-pm">
                Create PM Schedule
              </button>
              <button type="button" className="workspace-quick-action-btn" onClick={() => setActiveTab("documents")}>
                View Documents
              </button>
              <button type="button" className="workspace-quick-action-btn" onClick={() => setActiveTab("history")}>
                View History
              </button>
            </div>
          </div>

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            {/* RefGroup renders its own eyebrow-style title -- no second,
                redundant "Checklist Items" label wrapping it. */}
            <RefGroup title={checklistGroup.title} items={checklistGroup.items} emptyReason={checklistGroup.emptyReason} />
          </div>

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            <div className="eyebrow">LTSA Coverage</div>
            <div className="identity-status" style={{ marginTop: "var(--space-2)" }}>
              <StatusSignal tier={coverageMeta.tier} label={coverageMeta.label} />
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{coverageMeta.message}</p>
          </div>

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            <div className="eyebrow">Engineering Recommendation</div>
            {pm.recommendation ? (
              <h2 className="assessment-headline">{pm.recommendation}</h2>
            ) : (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>No recommendation available.</p>
            )}
          </div>
        </div>
      )}

      {activeTab === "engineering-ai" && (
        <div className="workspace-tab-body">
          {/* Placeholder only, per this domain's explicit rule -- no
              postEngineeringAI call is made for PM Schedules (unlike
              Pump/Seal/Work Order), so this is permanently the disclosed
              "not integrated" state, not a fabricated ready state. */}
          <Section id="engineering-ai-section" title="Engineering AI">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier="unavailable" label="Unavailable" dot={false} />
              <div style={{ marginTop: "var(--space-2)" }}>
                <InfoRow label="Reason" value="Engineering AI has not been integrated for PM Schedules yet." />
              </div>
            </div>
          </Section>
        </div>
      )}

      {activeTab === "documents" && (
        <div className="workspace-tab-body">
          {/* Documents deliberately keeps raw markup -- same documented
              exception as Pump/Seal/Work Order's own Documents section. */}
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
        </div>
      )}

      {activeTab === "history" && (
        <div className="workspace-tab-body">
          <Section id="recent-activities-section" title="Recent Activities">
            {pm.timeline.length === 0 ? (
              <div className="confidence-label ref-group-empty">No recent activity available.</div>
            ) : (
              pm.timeline.map((entry, i) => (
                <div className="part-item" key={`${entry.date}-${i}`}>
                  <div className="part-row">
                    <span className="part-name">{entry.event}</span>
                  </div>
                  <div className="part-meta">{entry.date}</div>
                </div>
              ))
            )}
          </Section>

          <Section id="related-engineering-section" title="Related Engineering">
            <div style={{ marginTop: "var(--space-3)" }}>
              {relatedGroups.map((g) => (
                <RefGroup key={g.id} title={g.title} items={g.items} emptyReason={g.emptyReason} />
              ))}
            </div>
          </Section>
        </div>
      )}

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="PM Drawing">
        <div className="drawing-thumb" />
        <p>No drawing data available. Drawing Workspace does not yet have a backend.</p>
      </PumpWorkspaceDrawer>
    </div>
  );
}

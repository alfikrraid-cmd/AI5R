import { useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import AssetIdentityHeader, { HealthCard } from "./AssetIdentityHeader";
import WorkspaceTabStrip from "./WorkspaceTabStrip";
import { IconClipboard } from "./PumpWorkspaceIcons";
import { Section, InfoRow, StatusSignal, RefGroup } from "./open-design";
import { statusLabel } from "../utils/workOrderStatus";
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
 * UI-D2A -- Work Order Workspace, migrated from the pre-UI-D1.2 Open
 * Design hierarchy (ChromeBar/crumb + workspace-grid/object-column/
 * inspector-rail + sticky Action Bar -- MWO-LTSA-055's original shape,
 * byte-identical in spirit to Pump/Seal before their own UI-D1.2 rebuild)
 * to Chief's approved reference: AssetIdentityHeader + WorkspaceTabStrip +
 * tabbed sections, exactly the same shared components PumpOpenDesignView.jsx/
 * SealOpenDesignView.jsx already use. This is a migration, not a redesign
 * of the underlying domain data or behavior -- every field/section below
 * is the same real, already-fetched value the old hierarchy rendered,
 * just regrouped into tabs:
 * - Overview: old Identity/Hero + "Work Order Overview" + "Current
 *   Status" + "LTSA Coverage" + "Description" sections, plus a new Quick
 *   Actions card (Buka Pump / Open PM Workspace / View Documents / View
 *   History) mirroring Pump's own Overview Quick Actions card -- "View
 *   Documents"/"View History" are local tab switches (no new navigation),
 *   "Buka Pump"/"Open PM Workspace" reuse the exact onOpenPump/
 *   onOpenPMWorkspace handlers the old sticky Action Bar already wired.
 * - AI Insight: old "Engineering AI" section, unchanged content/props.
 * - Documents: old raw-markup Documents section, unchanged (same
 *   Pump/Seal/PM "eyebrow + button deviates from Section's generic
 *   shape" documented exception).
 * - History: old "Recent Activities" (Inspector Rail) + "Related
 *   Engineering" section, combined onto one tab (Work Order has no
 *   Asset360-style numeric analytics to warrant a separate Performance
 *   tab, unlike Pump).
 *
 * Data discipline (unchanged): every field shows real, already-fetched
 * data or an honest empty state -- never fabricated.
 */

const STATUS_TIER = {
  OPEN: "attention",
  IN_PROGRESS: "attention",
  ON_HOLD: "neutral",
  COMPLETED: "normal",
  CANCELLED: "critical",
};

function statusMeta(status) {
  return { tier: STATUS_TIER[status] ?? "neutral", label: statusLabel(status) ?? "Unknown" };
}

const WORK_ORDER_TABS = [
  { key: "overview", label: "Overview" },
  { key: "ai-insight", label: "AI Insight" },
  { key: "documents", label: "Documents" },
  { key: "history", label: "History" },
];

export default function WorkOrderOpenDesignView({
  workOrder,
  relatedPMRecords = [],
  cmRecords = [],
  relatedWorkOrders = [],
  onOpenPump,
  onOpenDrawing,
  onOpenPMWorkspace,
  onBack,
  aiResponse,
  aiReady,
  aiStatusText,
  aiStatusVariant,
  aiStatusLabel,
}) {
  const [drawer, setDrawer] = useState(null); // null | "drawing"
  const [activeTab, setActiveTab] = useState("overview");

  const meta = statusMeta(workOrder.status);
  const covered = workOrder.area !== null;

  // LTSA Coverage: conditional, like PM's/Seal's -- workOrder.area is only
  // non-null when withResolvedArea's getWorkOrderAsset() call actually
  // resolved a real asset (workOrderMapping.js), so this is a real,
  // already-computed fact, not a fabricated derivation.
  const coverageMeta = covered
    ? { tier: "normal", label: "LTSA Covered", message: "Linked to an LTSA-covered asset." }
    : {
        tier: "neutral",
        label: "Coverage Unknown",
        message: "This work order's asset could not be resolved to an LTSA-covered asset.",
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
      items: relatedWorkOrders.map((item) => ({ key: item.id, name: item.id, meta: item.title, flagLabel: item.status })),
      emptyReason: dataEmptyReason,
    },
  ];

  return (
    <div className="ltsa-open-design" data-testid="workorder-open-design">
      <AssetIdentityHeader
        icon={<IconClipboard />}
        tag={workOrder.id}
        name={workOrder.title}
        subtitle={
          workOrder.equipmentTag
            ? `Asset ${workOrder.equipmentTag}${workOrder.area ? ` · ${workOrder.area}` : ""}`
            : "Asset unknown"
        }
        onBack={onBack}
      >
        <HealthCard label="Status" value={meta.label} tone={meta.tier} />
        <HealthCard label="Priority" value={workOrder.priority ?? "N/A"} />
      </AssetIdentityHeader>

      <WorkspaceTabStrip items={WORK_ORDER_TABS} activeKey={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" && (
        <div className="workspace-overview-grid">
          <div className="workspace-overview-card" data-od-id="identity-section">
            <div className="eyebrow">Asset Information</div>
            <InfoRow label="Work Order" value={workOrder.id} valueClassName="mono" />
            <InfoRow label="Equipment" value={workOrder.equipmentTag ?? "N/A"} />
            <InfoRow label="Work Type" value={workOrder.workType ?? "N/A"} />
            <InfoRow label="Created Date" value={workOrder.createdDate ?? "N/A"} />
            <InfoRow label="Due Date" value={workOrder.dueDate ?? "N/A"} />
          </div>

          <div className="workspace-overview-card">
            <div className="eyebrow">Classification &amp; Assignment</div>
            <InfoRow label="Priority" value={workOrder.priority ?? "N/A"} />
            <InfoRow label="Assigned Technician" value={workOrder.assignedTechnician ?? "N/A"} />
            <InfoRow label="Requested By" value={workOrder.requestedBy ?? "N/A"} />
            <InfoRow label="Status" value={meta.label} />
          </div>

          <div className="workspace-overview-card">
            <div className="eyebrow">Quick Actions</div>
            <div className="workspace-quick-actions">
              {workOrder.equipmentTag && (
                <button type="button" className="workspace-quick-action-btn" onClick={() => onOpenPump?.(workOrder.equipmentTag)} data-od-id="action-bar-open-pump">
                  Buka Pump →
                </button>
              )}
              {workOrder.workType === "PM" && onOpenPMWorkspace && (
                <button type="button" className="workspace-quick-action-btn" onClick={onOpenPMWorkspace} data-od-id="action-bar-open-pm-workspace">
                  Open PM Workspace
                </button>
              )}
              <button type="button" className="workspace-quick-action-btn" onClick={() => setActiveTab("documents")}>
                View Documents
              </button>
              <button type="button" className="workspace-quick-action-btn" onClick={() => setActiveTab("history")}>
                View History
              </button>
            </div>
          </div>

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            <div className="eyebrow">LTSA Coverage</div>
            <div className="identity-status" style={{ marginTop: "var(--space-2)" }}>
              <StatusSignal tier={coverageMeta.tier} label={coverageMeta.label} />
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{coverageMeta.message}</p>
          </div>

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            <div className="eyebrow">Description</div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>
              {workOrder.description || "No description provided."}
            </p>
          </div>
        </div>
      )}

      {activeTab === "ai-insight" && (
        <div className="workspace-tab-body">
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
        </div>
      )}

      {activeTab === "documents" && (
        <div className="workspace-tab-body">
          {/* Documents deliberately keeps raw markup -- same documented
              exception as Pump/Seal/PM's own Documents section: its
              eyebrow sits inside .section-head alongside a button,
              deviating from the generic Section shape. */}
          <section className="assessment-section" data-od-id="documents-section">
            <div className="section-head">
              <span className="eyebrow">Documents</span>
              <button
                type="button"
                className="btn-link"
                onClick={() => { onOpenDrawing?.(workOrder.equipmentTag); setDrawer("drawing"); }}
                data-od-id="open-drawing-link"
              >
                Buka Drawing →
              </button>
            </div>
            <div style={{ marginTop: "var(--space-2)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Document Types</div>
              <InfoRow label="Drawing" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Work Instruction" value="—" valueClassName="ref-group-empty" />
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
            {workOrder.timeline.length === 0 ? (
              <div className="confidence-label ref-group-empty">No recent activity available.</div>
            ) : (
              workOrder.timeline.map((entry, i) => (
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

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="Work Order Drawing">
        <div className="drawing-thumb" />
        <p>No drawing data available. Drawing Workspace does not yet have a backend.</p>
      </PumpWorkspaceDrawer>
    </div>
  );
}

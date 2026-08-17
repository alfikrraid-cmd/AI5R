import { useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import { Section, InfoRow, StatusSignal, RailSection, ActionBar, RefGroup } from "./open-design";
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
 * MWO-LTSA-055 -- Work Order Workspace, migrated to the same LTSA Open
 * Design information hierarchy as Pump/Seal/PM (PumpOpenDesignView.jsx,
 * SealOpenDesignView.jsx, PMOpenDesignView.jsx). Built entirely from the
 * shared components/open-design/ Kit (Section/InfoRow/StatusSignal/
 * RailSection/ActionBar/RefGroup, MWO-LTSA-050B) and PumpWorkspaceDrawer --
 * no new design language, no new CSS.
 *
 * Domain adaptation from Pump/Seal/PM's hierarchy (documented, not silent):
 * - Like PM (and unlike Pump), workOrder.equipmentTag is the real asset
 *   code directly (workOrderMapping.js: equipmentTag <- asset_code), but
 *   LTSA Coverage is CONDITIONAL like PM's/Seal's: workOrder.area is only
 *   resolved (withResolvedArea, workOrderMapping.js) when the asset_code
 *   successfully looks up via the existing Asset API. `workOrder.area !==
 *   null` is the same kind of real, already-computed "is this actually
 *   LTSA-covered" signal PM's pm.area !== null is -- not a fabricated
 *   derivation.
 * - Engineering AI is REAL here, unlike PM's permanent placeholder --
 *   WorkOrder.jsx already calls postEngineeringAI for every selected work
 *   order (Golden Reference pattern, same as Pump/Seal). This section
 *   reuses the exact same aiReady-branch markup/component set Pump/Seal's
 *   Open Design views already use, verbatim.
 * - Description has no Pump/Seal/PM precedent (none of those objects carry
 *   free-text prose) -- rendered as its own Section with a single prose
 *   paragraph, the same "real field, honest empty state" discipline as
 *   every other field here.
 * - Related Engineering mirrors PM's five groups (Related PM / Related
 *   Condition Monitoring / Related Failure Analysis / Related CM Reports /
 *   Related Work Orders). Related PM/Related CM Reports reuse
 *   getPMSchedules()/getCMReports() + mapPMScheduleRecord/mapCMReportRecord,
 *   the same already-wired calls Seal.jsx/PM.jsx use, filtered client-side
 *   by equipmentTag. Related Work Orders is derived from the work order
 *   list WorkOrder.jsx already has loaded (same equipmentTag, excluding
 *   this record) -- no new fetch, more complete than PM's own always-[]
 *   pm.relatedWorkOrders field since WorkOrder.jsx uniquely already holds
 *   the full sibling list in state. Related Condition Monitoring/Failure
 *   Analysis have no data source, same as Pump/PM's identical empty groups.
 * - Action Bar's one real, already-wired action is "Open PM Workspace"
 *   (only when workType === "PM", the exact same onOpenPMWorkspace handler
 *   WorkOrderDetailPanel.jsx used) -- the same "re-expose an existing
 *   page-level action from the sticky bar" pattern PM's "Create PM
 *   Schedule" already establishes. No new handler invented.
 * - Documents section keeps PM/Pump/Seal's own raw-markup exception
 *   (eyebrow + button inside .section-head, deviating from Section's
 *   generic shape).
 *
 * Data discipline (never fabricate): identical to PumpOpenDesignView.jsx/
 * SealOpenDesignView.jsx/PMOpenDesignView.jsx -- every field shows real,
 * already-fetched data or an honest empty state. requestedBy is rendered
 * as "--" when absent (workOrderMapping.js: intentionally never set this
 * sprint, ADR-WO-003) -- an honestly disclosed unimplemented field, not a
 * fabrication.
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

export default function WorkOrderOpenDesignView({
  workOrder,
  relatedPMRecords = [],
  cmRecords = [],
  relatedWorkOrders = [],
  onOpenPump,
  onOpenDrawing,
  onOpenPMWorkspace,
  aiResponse,
  aiReady,
  aiStatusText,
  aiStatusVariant,
  aiStatusLabel,
}) {
  const [drawer, setDrawer] = useState(null); // null | "drawing"

  const meta = statusMeta(workOrder.status);
  const covered = workOrder.area !== null;

  // LTSA Coverage: conditional, like PM's -- workOrder.area is only
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
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            {workOrder.equipmentTag ? (
              <button
                type="button"
                className="crumb-link"
                onClick={() => onOpenPump?.(workOrder.equipmentTag)}
                data-od-id="crumb-pump-link"
              >
                {workOrder.equipmentTag}
              </button>
            ) : (
              <span>Unknown Asset</span>
            )}
            <span className="sep">›</span><span>Work Order</span>
            <span className="sep">›</span><b>{workOrder.id}</b>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>{workOrder.title}</h1>
            <div className="identity-status">
              <StatusSignal tier={meta.tier} label={meta.label} />
              <span className="running-line">
                <span className="dot-sm" />
                {workOrder.equipmentTag ? `Asset ${workOrder.equipmentTag}${workOrder.area ? ` · ${workOrder.area}` : ""}` : "Asset unknown"}
              </span>
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Identity</div>
              <InfoRow label="Work Order" value={workOrder.id} valueClassName="mono" />
              <InfoRow label="Equipment" value={workOrder.equipmentTag ?? "—"} />
              <InfoRow label="Work Type" value={workOrder.workType ?? "—"} />
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Technical</div>
              <InfoRow label="Priority" value={workOrder.priority ?? "—"} />
              <InfoRow label="Assigned Technician" value={workOrder.assignedTechnician ?? "—"} />
              <InfoRow label="Due Date" value={workOrder.dueDate ?? "—"} />
            </div>
          </section>

          <Section id="work-order-overview-section" title="Work Order Overview">
            <div className="assessment-columns" style={{ marginTop: "var(--space-3)" }}>
              <div>
                <div className="eyebrow">Classification</div>
                <InfoRow label="Work Type" value={workOrder.workType ?? "—"} />
                <InfoRow label="Priority" value={workOrder.priority ?? "—"} />
              </div>
              <div>
                <div className="eyebrow">Assignment</div>
                <InfoRow label="Assigned Technician" value={workOrder.assignedTechnician ?? "—"} />
                <InfoRow label="Requested By" value={workOrder.requestedBy ?? "—"} />
              </div>
            </div>
          </Section>

          <Section id="current-status-section" title="Current Status">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Status" value={meta.label} />
              <InfoRow label="Created Date" value={workOrder.createdDate ?? "Unknown"} />
              <InfoRow label="Due Date" value={workOrder.dueDate ?? "Unknown"} />
              <InfoRow label="Coverage" value={coverageMeta.label} />
            </div>
          </Section>

          <Section id="coverage-section" title="LTSA Coverage">
            <div className="identity-status" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier={coverageMeta.tier} label={coverageMeta.label} />
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{coverageMeta.message}</p>
          </Section>

          <Section id="description-section" title="Description">
            <p className="confidence-label" style={{ marginTop: "var(--space-3)" }}>
              {workOrder.description || "No description provided."}
            </p>
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

          {/* Documents deliberately keeps raw markup, matching Pump/Seal/PM's
              own documented exception -- its eyebrow sits inside
              .section-head alongside a button, deviating from Section's
              generic shape. */}
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
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="work-order-status-section" title="Work Order Status">
            <StatusSignal tier={meta.tier} label={meta.label} />
          </RailSection>

          <RailSection id="priority-section" title="Priority">
            <div className="confidence-label">{workOrder.priority ?? "Unknown"}</div>
          </RailSection>

          <RailSection id="recent-activities-section" title="Recent Activities">
            {workOrder.timeline.length === 0 ? (
              <div className="confidence-label ref-group-empty">No recent activity available.</div>
            ) : (
              workOrder.timeline.map((entry, i) => (
                <div className="confidence-label" key={`${entry.date}-${i}`}>{entry.date} — {entry.event}</div>
              ))
            )}
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={`${workOrder.id} · ${meta.label}`}
        metaPrimary={coverageMeta.label}
        metaLabel="Due Date"
        metaValue={workOrder.dueDate ?? "Unknown"}
      >
        {workOrder.equipmentTag && (
          <button type="button" className="btn-link" onClick={() => onOpenPump?.(workOrder.equipmentTag)} data-od-id="action-bar-open-pump">
            Buka Pump →
          </button>
        )}
        {workOrder.workType === "PM" && onOpenPMWorkspace && (
          <button type="button" className="btn-primary" onClick={onOpenPMWorkspace} data-od-id="action-bar-open-pm-workspace">
            Open PM Workspace
          </button>
        )}
      </ActionBar>

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="Work Order Drawing">
        <div className="drawing-thumb" />
        <p>No drawing data available. Drawing Workspace does not yet have a backend.</p>
      </PumpWorkspaceDrawer>
    </div>
  );
}

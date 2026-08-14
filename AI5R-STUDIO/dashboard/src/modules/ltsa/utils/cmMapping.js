import { getPump } from "../../../api/ai5rClient";

/**
 * API-to-CM-Report-UI field mapping (APP-CM-001, per ADR-CM-001):
 * cm_report_code -> id, asset_code -> equipmentTag (and relatedPump --
 * ADR-CM-001's Decision table has no separate stored concept for
 * relatedPump; every sample record already had relatedPump ===
 * equipmentTag), work_order_code -> relatedWorkOrder,
 * failure_category/failure_description/root_cause/immediate_action/
 * corrective_action/downtime_hours/priority/status map directly,
 * assigned_to -> assignedTechnician.
 *
 * timeline is left as an empty array -- ADR-CM-001 classifies it as only
 * approximately derivable (via asset_code, not a precise per-incident
 * link) and its Required Frontend Changes section scopes this migration
 * to "fetch-on-mount, mapping layer, loading/error states, per-row area
 * resolution" only, the same scope PM.jsx's migration was held to for its
 * own analogous relatedWorkOrders/timeline fields. Empty, never
 * fabricated -- CMDetailPanel.jsx calls unguarded `cm.timeline.map(...)`,
 * so this is also required for crash prevention.
 *
 * area is resolved separately (see withResolvedArea) by reusing the
 * existing Pump API, identical to pmMapping.js's withResolvedArea --
 * every sample CM report targets a pump specifically, and no dedicated
 * CM-Report asset-resolution endpoint exists (unlike Work Order's
 * WO-BE-003); reusing getPump() directly degrades gracefully to null for
 * any non-pump asset_code.
 */
export function mapCMReportRecord(record) {
  return {
    id: record.cm_report_code,
    equipmentTag: record.asset_code,
    area: null,
    failureCategory: record.failure_category,
    severity: record.severity,
    priority: record.priority,
    failureDescription: record.failure_description,
    rootCause: record.root_cause,
    immediateAction: record.immediate_action,
    correctiveAction: record.corrective_action,
    downtimeHours: record.downtime_hours,
    assignedTechnician: record.assigned_to,
    relatedPump: record.asset_code,
    relatedWorkOrder: record.work_order_code,
    status: record.status,
    timeline: [],
    // MWO-LTSA-054 -- structurally present, always null: cm_report has no
    // recommendation column. Same "Derived, not fabricated" precedent as
    // pumpMapping.js/sealMapping.js/pmMapping.js's own recommendation field.
    recommendation: null,
  };
}

/**
 * Resolves `area` by reusing the existing Pump API (getPump), for one
 * already-mapped CM report. Never throws -- an unresolved asset (not a
 * pump, unknown tag, or a network failure) leaves `area: null`, the same
 * "honestly absent, never fabricated" convention as pmMapping.js.
 */
export async function withResolvedArea(cm) {
  if (!cm.equipmentTag) {
    return cm;
  }

  try {
    const pump = await getPump(cm.equipmentTag);
    return { ...cm, area: pump?.area ?? null };
  } catch {
    return cm;
  }
}

import { getPump } from "../../../api/ai5rClient";

/**
 * API-to-PM-Schedule-UI field mapping (APP-PM-001, per ADR-PM-001):
 * pm_schedule_code -> id, asset_code -> equipmentTag, trigger_type ->
 * triggerType, assigned_to -> assignedTechnician,
 * estimated_duration_hours -> estimatedDurationHours map directly.
 *
 * relatedWorkOrders and timeline are left as empty arrays -- neither is
 * derivable yet (WO-PM-003's relatedWorkOrders derivation and a PM-scoped
 * Maintenance History timeline endpoint were both left for future MWOs by
 * ADR-PM-001; only the table/gateway/workflows and list/detail routes
 * exist so far, per WO-PM-001/WO-PM-002). Empty, never fabricated --
 * PMDetailPanel.jsx calls unguarded `.map()`/`.length` on both, so this is
 * also required for crash prevention, the same distinction ADR-PUMP-001
 * drew between defensive typing and business-data decisions.
 *
 * area is resolved separately (see withResolvedArea) by reusing the
 * existing Pump API -- every PM Schedule sample record targets a pump
 * specifically, and no dedicated PM-Schedule asset-resolution endpoint
 * exists (unlike Work Order's WO-BE-003); reusing getPump() directly
 * degrades gracefully to null for any non-pump asset_code.
 */
function formatDateOnly(value) {
  if (!value) {
    return null;
  }

  return String(value).slice(0, 10);
}

// ADR-PM-001: status ACTIVE/ON_HOLD are stored; DUE_SOON/OVERDUE are
// computed from next_due vs. the current date, never stored. The ADR did
// not pin an exact "due soon" window -- 7 days is this migration's
// disclosed, adjustable assumption, not a fabricated business fact.
const DUE_SOON_WINDOW_DAYS = 7;

function computeDisplayStatus(status, nextDue) {
  if (status !== "ACTIVE" || !nextDue) {
    return status;
  }

  const dueDate = new Date(nextDue);

  if (Number.isNaN(dueDate.getTime())) {
    return status;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  dueDate.setHours(0, 0, 0, 0);

  const daysUntilDue = Math.round((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  if (daysUntilDue < 0) {
    return "OVERDUE";
  }

  if (daysUntilDue <= DUE_SOON_WINDOW_DAYS) {
    return "DUE_SOON";
  }

  return "ACTIVE";
}

export function mapPMScheduleRecord(record) {
  const nextDue = formatDateOnly(record.next_due);

  return {
    id: record.pm_schedule_code,
    equipmentTag: record.asset_code,
    area: null,
    procedure: record.procedure,
    frequency: record.frequency,
    triggerType: record.trigger_type,
    checklist: Array.isArray(record.checklist) ? record.checklist : [],
    lastPerformed: formatDateOnly(record.last_performed),
    nextDue,
    assignedTechnician: record.assigned_to,
    estimatedDurationHours: record.estimated_duration_hours,
    relatedWorkOrders: [],
    status: computeDisplayStatus(record.status, nextDue),
    // MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- Edit Schedule needs the REAL
    // stored status (ACTIVE/ON_HOLD only, per this file's own comment
    // above) to prefill/submit, never the computed DUE_SOON/OVERDUE
    // display value `status` above already carries -- PATCHing a computed
    // value back as if it were a real stored one would corrupt the row.
    rawStatus: record.status,
    intervalUnit: record.interval_unit,
    effectiveDate: formatDateOnly(record.effective_date),
    timeline: [],
    // MWO-LTSA-053 -- structurally present, always null: pm_schedule has
    // no recommendation column (ADR-PM-001's real-column list above).
    // Same "Derived, not fabricated" precedent as pumpMapping.js/
    // sealMapping.js's own recommendation field.
    recommendation: null,
  };
}

/**
 * MWO-LTSA-PM-CM-REVIEW-UI-001 -- maps a pm_occurrence record (a real
 * field visit: activities/finding/preliminary+technical recommendation,
 * workflow/evidence attribution) to camelCase, mirroring
 * mapPMScheduleRecord's own field-by-field convention above. Distinct
 * from mapPMScheduleRecord: pm_occurrence and pm_schedule are two
 * different tables (see this file's own pm_schedule_code header note),
 * never merged into one shape. Column list matches
 * pm_occurrence_repository.py's _SELECT_COLUMNS exactly (this session's
 * own re-read of that file, not assumed).
 */
export function mapPMOccurrenceRecord(record) {
  return {
    id: record.pm_occurrence_code,
    pmScheduleCode: record.pm_schedule_code,
    equipmentTag: record.asset_code,
    assetType: record.asset_type,
    occurrenceDate: formatDateOnly(record.occurrence_date),
    activities: Array.isArray(record.activities) ? record.activities : [],
    finding: record.finding,
    // Phase 14 (this MWO): preliminaryRecommendation (TAP Engineer, set at
    // create/edit time) and technicalRecommendation (John Crane, set only
    // via technical-review) are distinct fields -- never merged into one,
    // never overwriting each other client-side either.
    preliminaryRecommendation: record.preliminary_recommendation,
    remarks: record.remarks,
    provenance: record.provenance,
    workflowStatus: record.workflow_status,
    submittedBy: record.submitted_by,
    submittedAt: record.submitted_at,
    reviewedBy: record.reviewed_by,
    reviewedAt: record.reviewed_at,
    returnReason: record.return_reason,
    technicalReviewedBy: record.technical_reviewed_by,
    technicalReviewedAt: record.technical_reviewed_at,
    technicalOutcome: record.technical_outcome,
    technicalComment: record.technical_comment,
    technicalRecommendation: record.technical_recommendation,
    createdBy: record.created_by,
    updatedBy: record.updated_by,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
    // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- historical-import
    // provenance (populated for workbook-sourced records e.g. "CM & PM
    // Summary HOC JUNI.xlsx"; undefined/null for live-entered ones, never
    // fabricated -- PMOccurrenceDetailPanel.jsx renders N/A for either).
    sourceWorkbookName: record.source_workbook_name,
    sourceSheetName: record.source_sheet_name,
    sourceRowNumber: record.source_row_number,
  };
}

/**
 * Resolves `area` by reusing the existing Pump API (getPump), for one
 * already-mapped PM schedule. Never throws -- an unresolved asset (not a
 * pump, unknown tag, or a network failure) leaves `area: null`, the same
 * "honestly absent, never fabricated" convention as the rest of this
 * mapping.
 */
export async function withResolvedArea(pm) {
  if (!pm.equipmentTag) {
    return pm;
  }

  try {
    const pump = await getPump(pm.equipmentTag);
    return { ...pm, area: pump?.area ?? null };
  } catch {
    return pm;
  }
}

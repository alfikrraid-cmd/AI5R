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

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- owner-approved authoritative
// lifecycle: PLANNED / ACTIVE / OVERDUE / COMPLETED / CANCELLED.
// COMPLETED/CANCELLED are real, application-set stored values (via the
// existing PATCH pm-schedules/{code} endpoint, or the new atomic
// schedule-completion in pm_occurrence_repository.create_draft()) and
// pass through unchanged -- never recomputed, never silently overwritten
// by a date comparison. PLANNED/ACTIVE/OVERDUE are computed from the
// stored status=ACTIVE + next_due vs. the current date, exactly the same
// "computed, never stored" precedent ADR-PM-001 already established for
// the old DUE_SOON/OVERDUE pair -- OVERDUE here supersedes that pair
// (superseded, not added to): expired-but-incomplete work is OVERDUE
// only, no separate "coming due soon" state was in the owner's approved
// vocabulary. ON_HOLD (a pre-existing stored value outside this MWO's own
// 5-state list) still passes through unchanged -- never invented over,
// never silently migrated.
//
// Month comparison, not a day-count window: a schedule is PLANNED while
// its next_due falls in a calendar month strictly after the current
// operational month (created this month, for next month, per the
// owner's own worked example), and becomes ACTIVE the moment the current
// month reaches that target month -- matching "September begins -> the
// September schedule becomes active" precisely, not an arbitrary N-day
// lookahead.
function computeDisplayStatus(status, nextDue) {
  if (status === "COMPLETED" || status === "CANCELLED") {
    return status;
  }

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

  if (dueDate.getTime() < today.getTime()) {
    return "OVERDUE";
  }

  const currentMonthKey = today.getFullYear() * 12 + today.getMonth();
  const dueMonthKey = dueDate.getFullYear() * 12 + dueDate.getMonth();

  if (dueMonthKey > currentMonthKey) {
    return "PLANNED";
  }

  return "ACTIVE";
}

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- "Normal operational UI should
// create schedules for NEXT MONTH... Derive next calendar month from
// current operational date... Do not silently create schedules for past
// months." Never hard-codes a month/year; always relative to `reference`
// (defaults to the real current date, overridable only for tests).
// Returns the 1st of next month as an ISO yyyy-mm-dd date-input value --
// a starting default the owner may still move to another future month via
// the same date input this already was (never a locked value).
export function nextMonthFirstDay(reference = new Date()) {
  const nextMonth = new Date(reference.getFullYear(), reference.getMonth() + 1, 1);
  // Never .toISOString() a local Date here: it converts through UTC, which
  // silently shifts the calendar day (sometimes back a full day) in any
  // timezone west of UTC -- exactly the "silently create a schedule for
  // the wrong month" bug this MWO's own "never past months" rule forbids.
  // Built from local Y/M components instead; the day is always "01".
  const year = nextMonth.getFullYear();
  const month = String(nextMonth.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}-01`;
}

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- "The source workbook identity
// is provenance, not schedule identity" -- ltsa_hoc_pm_cm_upsert.py's own
// build_unscheduled_reference() writes this exact "UNSCHEDULED::<workbook>"
// placeholder into pm_schedule_code/condition_monitoring_schedule_code for
// every historically-imported row with no real owning schedule (there is
// no separate "has a schedule" boolean to check instead). Shared by both
// pmMapping.js and conditionMonitoringMapping.js consumers that render a
// schedule-code field, so neither one ever presents this placeholder as if
// it were an operational schedule.
export function isUnscheduledPlaceholder(code) {
  return typeof code === "string" && code.startsWith("UNSCHEDULED::");
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
    // MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- the real stored
    // completion signal (DB default 'DONE', distinct from workflow_status)
    // needed by historicalBatchReviewClassification.js's READY_FOR_REVIEW
    // evidence check. Never previously mapped -- additive only.
    status: record.status,
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
    // MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- the July
    // document-extraction batch's own provenance pointer (e.g.
    // "document_field_extraction:DFE-..."), distinct from source_workbook_
    // name (June/January direct workbook imports never set this column).
    sourceReference: record.source_reference,
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

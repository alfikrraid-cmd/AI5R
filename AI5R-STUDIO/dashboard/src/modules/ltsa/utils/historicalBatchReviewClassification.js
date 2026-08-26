// MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- deterministic READY_FOR_
// REVIEW / NEEDS_ATTENTION classification for the July 2026 historical
// DRAFT backlog (MWO-018's own finding: provenance='HISTORICAL_IMPORT',
// source_reference='document_field_extraction:DFE-...'). Pure functions,
// no I/O -- classification is presentation triage only, never approval
// (a READY_FOR_REVIEW record is still DRAFT until a real human submits
// and a real John Crane Engineer finalizes it through the existing
// workflow; this module never transitions anything).
import { MEASUREMENT_PAIR_FIELDS, MEASUREMENT_SINGLE_FIELDS } from "./conditionMonitoringMeasurementFields";

const READY_FOR_REVIEW = "READY_FOR_REVIEW";
const NEEDS_ATTENTION = "NEEDS_ATTENTION";

// null = not part of this review queue at all (not a historical-import
// DRAFT record) -- distinct from NEEDS_ATTENTION, which IS in the queue
// but lacking evidence.
export function classifyPMOccurrence(occurrence) {
  if (occurrence.provenance !== "HISTORICAL_IMPORT" || occurrence.workflowStatus !== "DRAFT") {
    return null;
  }
  const hasPump = Boolean(occurrence.equipmentTag);
  const hasDate = Boolean(occurrence.occurrenceDate);
  const isDone = occurrence.status === "DONE";
  const hasActivities = Array.isArray(occurrence.activities) && occurrence.activities.length > 0;
  return hasPump && hasDate && isDone && hasActivities ? READY_FOR_REVIEW : NEEDS_ATTENTION;
}

export function classifyConditionMonitoringReading(reading) {
  if (reading.provenance !== "HISTORICAL_IMPORT" || reading.workflowStatus !== "DRAFT") {
    return null;
  }
  const hasPump = Boolean(reading.equipmentTag);
  const hasDate = Boolean(reading.readingDate);
  const hasMeasurement =
    MEASUREMENT_PAIR_FIELDS.some((field) => reading[field.deKey] != null || reading[field.ndeKey] != null) ||
    MEASUREMENT_SINGLE_FIELDS.some((field) => reading[field.key] != null);
  return hasPump && hasDate && hasMeasurement ? READY_FOR_REVIEW : NEEDS_ATTENTION;
}

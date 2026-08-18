import { getPump } from "../../../api/ai5rClient";

/**
 * API-to-Condition-Monitoring-UI field mapping (APP-CMON-001, per
 * ADR-CONDITION-MONITORING-001). First dedicated mapping file for this
 * domain: earlier, Asset 360's own timeline mapped condition_monitoring_
 * reading/schedule records inline (utils/maintenanceHistory.js), disclosed
 * at the time as reasonable only because no dedicated workspace page
 * existed yet to justify a separate file. That page now exists -- this
 * file is it, mirroring pmMapping.js/cmMapping.js's exact conventions.
 * (utils/maintenanceHistory.js's own inline mappers are untouched --
 * still correct for Asset 360's distinct "event stream row" shape, no
 * reason to force the two consumers onto one shared mapper.)
 */

function formatDateOnly(value) {
  if (!value) {
    return null;
  }

  return String(value).slice(0, 10);
}

export function mapConditionMonitoringScheduleRecord(record) {
  return {
    id: record.condition_monitoring_schedule_code,
    equipmentTag: record.asset_code,
    area: null,
    frequency: record.frequency,
    applicableParameters: Array.isArray(record.applicable_parameters) ? record.applicable_parameters : [],
  };
}

export function mapConditionMonitoringReadingRecord(record) {
  return {
    id: record.condition_monitoring_reading_code,
    scheduleCode: record.condition_monitoring_schedule_code,
    equipmentTag: record.asset_code,
    area: null,
    readingDate: formatDateOnly(record.reading_date),
    flushingTempDe: record.flushing_temp_de,
    flushingTempNde: record.flushing_temp_nde,
    quenchTempDe: record.quench_temp_de,
    quenchTempNde: record.quench_temp_nde,
    flushingInTempDe: record.flushing_in_temp_de,
    flushingInTempNde: record.flushing_in_temp_nde,
    flushingOutTempDe: record.flushing_out_temp_de,
    flushingOutTempNde: record.flushing_out_temp_nde,
    coolingWaterInTempDe: record.cooling_water_in_temp_de,
    coolingWaterInTempNde: record.cooling_water_in_temp_nde,
    coolingWaterOutTempDe: record.cooling_water_out_temp_de,
    coolingWaterOutTempNde: record.cooling_water_out_temp_nde,
    mechsealTempDe: record.mechseal_temp_de,
    mechsealTempNde: record.mechseal_temp_nde,
    leakDe: record.mechanical_seal_leak_de === true,
    leakNde: record.mechanical_seal_leak_nde === true,
    waterJacketTempDe: record.water_jacket_temp_de,
    waterJacketTempNde: record.water_jacket_temp_nde,
    suctionTemp: record.suction_temp,
    dischargeTemp: record.discharge_temp,
    pumpOperatingState: record.pump_operating_state,
    // MWO-LTSA-PM-CM-REVIEW-UI-001 -- migration-014 additions
    // (_MEASUREMENT_COLUMNS in condition_monitoring_reading_repository.py,
    // this session's own re-read of that file): pressure/vibration/
    // bearing-temp/motor-current fields the golden reports' Check Points
    // table has but the pre-existing mapping above did not yet surface.
    suctionPressure: record.suction_pressure,
    dischargePressure: record.discharge_pressure,
    quenchPressureDe: record.quench_pressure_de,
    quenchPressureNde: record.quench_pressure_nde,
    stuffingBoxTempDe: record.stuffing_box_temp_de,
    stuffingBoxTempNde: record.stuffing_box_temp_nde,
    sealGlandTempDe: record.seal_gland_temp_de,
    sealGlandTempNde: record.seal_gland_temp_nde,
    verticalVibrationDe: record.vertical_vibration_de,
    verticalVibrationNde: record.vertical_vibration_nde,
    horizontalVibrationDe: record.horizontal_vibration_de,
    horizontalVibrationNde: record.horizontal_vibration_nde,
    axialVibrationDe: record.axial_vibration_de,
    axialVibrationNde: record.axial_vibration_nde,
    bearingTempDe: record.bearing_temp_de,
    bearingTempNde: record.bearing_temp_nde,
    motorCurrent: record.motor_current,
    // Workflow/attribution columns (_WORKFLOW_COLUMNS, same repository) --
    // identical shape to mapPMOccurrenceRecord's own fields in
    // pmMapping.js, since pm_cm_workflow_service.py is the one shared
    // state machine for both domains (Phase 10).
    finding: record.finding,
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
  };
}

/**
 * Resolves `area` by reusing the existing Pump API (getPump), for one
 * already-mapped Schedule or Reading. Never throws -- an unresolved asset
 * leaves `area: null`, the same "honestly absent, never fabricated"
 * convention as pmMapping.js/cmMapping.js/workOrderMapping.js.
 */
export async function withResolvedArea(record) {
  if (!record.equipmentTag) {
    return record;
  }

  try {
    const pump = await getPump(record.equipmentTag);
    return { ...record, area: pump?.area ?? null };
  } catch {
    return record;
  }
}

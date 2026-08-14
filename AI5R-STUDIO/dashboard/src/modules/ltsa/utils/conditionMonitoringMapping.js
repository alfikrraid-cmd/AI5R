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

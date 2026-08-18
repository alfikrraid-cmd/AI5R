// MWO-LTSA-PM-CM-REVIEW-PRE-PUSH-CLOSURE-001 -- single source of truth for
// every enterable Condition Monitoring measurement field, shared by
// CreateConditionMonitoringReadingModal.jsx (create) and
// ConditionMonitoringReadingDetailPanel.jsx (edit draft/returned) so the
// two forms can never drift out of sync. A plain data/logic module, not a
// UI component or a second CM form -- it renders nothing.
//
// Column/unit provenance: condition_monitoring_reading_repository.py's own
// _MEASUREMENT_COLUMNS tuple (this session's own re-read of that file) is
// the authoritative field list; units match ConditionMonitoringReadingDetail
// Panel.jsx's own already-established tempValue/pressureValue/vibrationValue
// conventions (°C / bar / mm/s / A), not invented here. mechanical_seal_leak
// _de/nde is a nullable BOOLEAN column (CANONICAL_SCHEMA.sql) -- tri-state
// (not recorded / no leak / leak detected), never inferred from a blank
// field.

// DE/NDE paired NUMERIC fields. Every entry maps 1:1 to a real column pair
// already returned by mapConditionMonitoringReadingRecord() (conditionMonitoringMapping.js).
export const MEASUREMENT_PAIR_FIELDS = [
  { group: "Mechanical Seal Temp", deKey: "mechsealTempDe", ndeKey: "mechsealTempNde", deColumn: "mechseal_temp_de", ndeColumn: "mechseal_temp_nde", unit: "°C" },
  { group: "Quench Pressure", deKey: "quenchPressureDe", ndeKey: "quenchPressureNde", deColumn: "quench_pressure_de", ndeColumn: "quench_pressure_nde", unit: "bar" },
  { group: "Stuffing Box Temp", deKey: "stuffingBoxTempDe", ndeKey: "stuffingBoxTempNde", deColumn: "stuffing_box_temp_de", ndeColumn: "stuffing_box_temp_nde", unit: "°C" },
  { group: "Seal Gland Temp", deKey: "sealGlandTempDe", ndeKey: "sealGlandTempNde", deColumn: "seal_gland_temp_de", ndeColumn: "seal_gland_temp_nde", unit: "°C" },
  { group: "Vertical Vibration", deKey: "verticalVibrationDe", ndeKey: "verticalVibrationNde", deColumn: "vertical_vibration_de", ndeColumn: "vertical_vibration_nde", unit: "mm/s" },
  { group: "Horizontal Vibration", deKey: "horizontalVibrationDe", ndeKey: "horizontalVibrationNde", deColumn: "horizontal_vibration_de", ndeColumn: "horizontal_vibration_nde", unit: "mm/s" },
  { group: "Axial Vibration", deKey: "axialVibrationDe", ndeKey: "axialVibrationNde", deColumn: "axial_vibration_de", ndeColumn: "axial_vibration_nde", unit: "mm/s" },
  { group: "Bearing Temp", deKey: "bearingTempDe", ndeKey: "bearingTempNde", deColumn: "bearing_temp_de", ndeColumn: "bearing_temp_nde", unit: "°C" },
];

// Single (non-DE/NDE) NUMERIC fields.
export const MEASUREMENT_SINGLE_FIELDS = [
  { label: "Suction Temp", key: "suctionTemp", column: "suction_temp", unit: "°C" },
  { label: "Discharge Temp", key: "dischargeTemp", column: "discharge_temp", unit: "°C" },
  { label: "Suction Pressure", key: "suctionPressure", column: "suction_pressure", unit: "bar" },
  { label: "Discharge Pressure", key: "dischargePressure", column: "discharge_pressure", unit: "bar" },
  { label: "Motor Current", key: "motorCurrent", column: "motor_current", unit: "A" },
];

// Leak status pair -- tri-state, deliberately NOT in MEASUREMENT_PAIR_FIELDS
// (boolean, not numeric; own null-coercion rules).
export const LEAK_FIELD = {
  group: "Mechanical Seal Leak",
  deKey: "leakDe",
  ndeKey: "leakNde",
  deColumn: "mechanical_seal_leak_de",
  ndeColumn: "mechanical_seal_leak_nde",
};

// Blank input persists as NULL, never 0 -- Number("") is 0 in JS, so an
// empty string must be caught explicitly before the numeric conversion.
export function parseOptionalNumber(rawValue) {
  return rawValue === "" || rawValue == null ? null : Number(rawValue);
}

export function numberToFieldValue(value) {
  return value == null ? "" : String(value);
}

// Leak tri-state: "" (not recorded) / "false" (no leak) / "true" (leak
// detected) <-> null / false / true. A blank selection must never be sent
// as false -- that would fabricate "no leak" for a field nobody checked.
export function parseLeakStatus(rawValue) {
  if (rawValue === "true") return true;
  if (rawValue === "false") return false;
  return null;
}

export function leakStatusToFieldValue(value) {
  if (value === true) return "true";
  if (value === false) return "false";
  return "";
}

// Builds the full snake_case `measurements` payload
// createConditionMonitoringReading/updateConditionMonitoringReadingDraft
// expect, from a camelCase form-values object (string inputs from either
// the Create modal or the Edit panel). Single source of null-coercion
// logic -- both forms call this, so they cannot drift.
export function buildMeasurementsPayload(formValues) {
  const payload = {};

  for (const field of MEASUREMENT_PAIR_FIELDS) {
    payload[field.deColumn] = parseOptionalNumber(formValues[field.deKey]);
    payload[field.ndeColumn] = parseOptionalNumber(formValues[field.ndeKey]);
  }
  for (const field of MEASUREMENT_SINGLE_FIELDS) {
    payload[field.column] = parseOptionalNumber(formValues[field.key]);
  }
  payload[LEAK_FIELD.deColumn] = parseLeakStatus(formValues[LEAK_FIELD.deKey]);
  payload[LEAK_FIELD.ndeColumn] = parseLeakStatus(formValues[LEAK_FIELD.ndeKey]);
  payload.pump_operating_state = formValues.pumpOperatingState || null;

  return payload;
}

// Every field key this module manages, defaulted to "" (empty/unset) --
// the base for a fresh Create form.
export function emptyMeasurementFormValues() {
  const values = { pumpOperatingState: "" };
  for (const field of MEASUREMENT_PAIR_FIELDS) {
    values[field.deKey] = "";
    values[field.ndeKey] = "";
  }
  for (const field of MEASUREMENT_SINGLE_FIELDS) {
    values[field.key] = "";
  }
  values[LEAK_FIELD.deKey] = "";
  values[LEAK_FIELD.ndeKey] = "";
  return values;
}

// Initializes edit-form state from an already-mapped (camelCase) reading
// record -- the Edit panel's own starting point, so an existing DRAFT/
// RETURNED_FOR_CORRECTION reading's real persisted values are never lost
// when the technician opens the record for correction.
export function measurementFormValuesFromReading(reading) {
  const values = { pumpOperatingState: reading.pumpOperatingState ?? "" };
  for (const field of MEASUREMENT_PAIR_FIELDS) {
    values[field.deKey] = numberToFieldValue(reading[field.deKey]);
    values[field.ndeKey] = numberToFieldValue(reading[field.ndeKey]);
  }
  for (const field of MEASUREMENT_SINGLE_FIELDS) {
    values[field.key] = numberToFieldValue(reading[field.key]);
  }
  values[LEAK_FIELD.deKey] = leakStatusToFieldValue(reading[LEAK_FIELD.deKey]);
  values[LEAK_FIELD.ndeKey] = leakStatusToFieldValue(reading[LEAK_FIELD.ndeKey]);
  return values;
}

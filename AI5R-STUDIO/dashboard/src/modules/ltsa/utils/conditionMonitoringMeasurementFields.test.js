import { describe, expect, it } from "vitest";
import {
  MEASUREMENT_PAIR_FIELDS,
  MEASUREMENT_SINGLE_FIELDS,
  LEAK_FIELD,
  parseOptionalNumber,
  numberToFieldValue,
  parseLeakStatus,
  leakStatusToFieldValue,
  buildMeasurementsPayload,
  emptyMeasurementFormValues,
  measurementFormValuesFromReading,
} from "./conditionMonitoringMeasurementFields";

describe("parseOptionalNumber -- blank must never become zero", () => {
  it("returns null for an empty string, not 0", () => {
    expect(parseOptionalNumber("")).toBeNull();
  });

  it("returns null for null/undefined", () => {
    expect(parseOptionalNumber(null)).toBeNull();
    expect(parseOptionalNumber(undefined)).toBeNull();
  });

  it("returns the real number when the technician explicitly enters 0", () => {
    expect(parseOptionalNumber("0")).toBe(0);
  });

  it("parses a normal decimal value", () => {
    expect(parseOptionalNumber("84.5")).toBe(84.5);
  });
});

describe("numberToFieldValue", () => {
  it("renders null/undefined as an empty string (never '0')", () => {
    expect(numberToFieldValue(null)).toBe("");
    expect(numberToFieldValue(undefined)).toBe("");
  });

  it("renders a real zero as the string '0', not blank", () => {
    expect(numberToFieldValue(0)).toBe("0");
  });

  it("round-trips a real value", () => {
    expect(numberToFieldValue(84.5)).toBe("84.5");
  });
});

describe("leak tri-state -- never infer NO LEAK from a blank field", () => {
  it("parseLeakStatus('') is null (not recorded), not false", () => {
    expect(parseLeakStatus("")).toBeNull();
  });

  it("parseLeakStatus distinguishes 'true'/'false' strings", () => {
    expect(parseLeakStatus("true")).toBe(true);
    expect(parseLeakStatus("false")).toBe(false);
  });

  it("leakStatusToFieldValue round-trips null/true/false to '', 'true', 'false'", () => {
    expect(leakStatusToFieldValue(null)).toBe("");
    expect(leakStatusToFieldValue(undefined)).toBe("");
    expect(leakStatusToFieldValue(true)).toBe("true");
    expect(leakStatusToFieldValue(false)).toBe("false");
  });
});

describe("buildMeasurementsPayload", () => {
  it("sends null (not 0/false) for every untouched field from a blank form", () => {
    const payload = buildMeasurementsPayload(emptyMeasurementFormValues());

    for (const field of MEASUREMENT_PAIR_FIELDS) {
      expect(payload[field.deColumn]).toBeNull();
      expect(payload[field.ndeColumn]).toBeNull();
    }
    for (const field of MEASUREMENT_SINGLE_FIELDS) {
      expect(payload[field.column]).toBeNull();
    }
    expect(payload[LEAK_FIELD.deColumn]).toBeNull();
    expect(payload[LEAK_FIELD.ndeColumn]).toBeNull();
    expect(payload.pump_operating_state).toBeNull();
  });

  it("preserves DE and NDE as two independent values, never collapsed", () => {
    const values = emptyMeasurementFormValues();
    values.bearingTempDe = "61";
    values.bearingTempNde = "";

    const payload = buildMeasurementsPayload(values);

    expect(payload.bearing_temp_de).toBe(61);
    expect(payload.bearing_temp_nde).toBeNull();
  });

  it("preserves an explicitly entered zero (never coerced to null)", () => {
    const values = emptyMeasurementFormValues();
    values.motorCurrent = "0";

    expect(buildMeasurementsPayload(values).motor_current).toBe(0);
  });

  it("maps leak DE/NDE independently -- one leaking, one not recorded", () => {
    const values = emptyMeasurementFormValues();
    values.leakDe = "true";
    values.leakNde = "";

    const payload = buildMeasurementsPayload(values);

    expect(payload.mechanical_seal_leak_de).toBe(true);
    expect(payload.mechanical_seal_leak_nde).toBeNull();
  });

  it("maps every migration-014 field to its real snake_case column name", () => {
    const values = emptyMeasurementFormValues();
    values.suctionPressure = "3.2";
    values.dischargePressure = "11.4";
    values.quenchPressureDe = "1.1";
    values.quenchPressureNde = "1.2";
    values.stuffingBoxTempDe = "70";
    values.stuffingBoxTempNde = "71";
    values.sealGlandTempDe = "65";
    values.sealGlandTempNde = "66";
    values.verticalVibrationDe = "2.1";
    values.verticalVibrationNde = "2.2";
    values.horizontalVibrationDe = "1.9";
    values.horizontalVibrationNde = "2.0";
    values.axialVibrationDe = "0.8";
    values.axialVibrationNde = "0.9";
    values.bearingTempDe = "61";
    values.bearingTempNde = "58";
    values.motorCurrent = "22.1";

    const payload = buildMeasurementsPayload(values);

    expect(payload).toMatchObject({
      suction_pressure: 3.2,
      discharge_pressure: 11.4,
      quench_pressure_de: 1.1,
      quench_pressure_nde: 1.2,
      stuffing_box_temp_de: 70,
      stuffing_box_temp_nde: 71,
      seal_gland_temp_de: 65,
      seal_gland_temp_nde: 66,
      vertical_vibration_de: 2.1,
      vertical_vibration_nde: 2.2,
      horizontal_vibration_de: 1.9,
      horizontal_vibration_nde: 2.0,
      axial_vibration_de: 0.8,
      axial_vibration_nde: 0.9,
      bearing_temp_de: 61,
      bearing_temp_nde: 58,
      motor_current: 22.1,
    });
  });
});

describe("measurementFormValuesFromReading -- edit-form initialization from a real record", () => {
  it("round-trips a fully-populated reading back into form-editable strings", () => {
    const reading = {
      pumpOperatingState: "RUNNING",
      mechsealTempDe: 84,
      mechsealTempNde: 79,
      suctionTemp: 42,
      dischargeTemp: 55,
      suctionPressure: 3.2,
      dischargePressure: 11.4,
      quenchPressureDe: 1.1,
      quenchPressureNde: null,
      stuffingBoxTempDe: 70,
      stuffingBoxTempNde: 71,
      sealGlandTempDe: null,
      sealGlandTempNde: null,
      verticalVibrationDe: 2.1,
      verticalVibrationNde: 2.2,
      horizontalVibrationDe: null,
      horizontalVibrationNde: null,
      axialVibrationDe: null,
      axialVibrationNde: null,
      bearingTempDe: 61,
      bearingTempNde: 58,
      motorCurrent: 0,
      leakDe: true,
      leakNde: false,
    };

    const values = measurementFormValuesFromReading(reading);

    expect(values.mechsealTempDe).toBe("84");
    expect(values.quenchPressureDe).toBe("1.1");
    expect(values.quenchPressureNde).toBe(""); // null -- not "0"
    expect(values.motorCurrent).toBe("0"); // real zero preserved, not blank
    expect(values.leakDe).toBe("true");
    expect(values.leakNde).toBe("false");
    expect(values.sealGlandTempDe).toBe("");
  });

  it("a reading with no measurements yet round-trips to an all-blank form, never fabricated zeros", () => {
    const reading = { pumpOperatingState: null };
    const values = measurementFormValuesFromReading(reading);

    for (const field of MEASUREMENT_PAIR_FIELDS) {
      expect(values[field.deKey]).toBe("");
      expect(values[field.ndeKey]).toBe("");
    }
    expect(values.leakDe).toBe("");
    expect(values.leakNde).toBe("");
    expect(values.pumpOperatingState).toBe("");
  });

  it("round-trip through buildMeasurementsPayload preserves every real value unmodified", () => {
    const reading = {
      pumpOperatingState: "STANDBY",
      mechsealTempDe: 84.5,
      mechsealTempNde: 79.2,
      suctionTemp: 42,
      dischargeTemp: 55,
      suctionPressure: 3.2,
      dischargePressure: 11.4,
      quenchPressureDe: 1.1,
      quenchPressureNde: 1.2,
      stuffingBoxTempDe: 70,
      stuffingBoxTempNde: 71,
      sealGlandTempDe: 65,
      sealGlandTempNde: 66,
      verticalVibrationDe: 2.1,
      verticalVibrationNde: 2.2,
      horizontalVibrationDe: 1.9,
      horizontalVibrationNde: 2.0,
      axialVibrationDe: 0.8,
      axialVibrationNde: 0.9,
      bearingTempDe: 61,
      bearingTempNde: 58,
      motorCurrent: 22.1,
      leakDe: false,
      leakNde: false,
    };

    const payload = buildMeasurementsPayload(measurementFormValuesFromReading(reading));

    expect(payload.mechseal_temp_de).toBe(84.5);
    expect(payload.mechseal_temp_nde).toBe(79.2);
    expect(payload.bearing_temp_de).toBe(61);
    expect(payload.motor_current).toBe(22.1);
    expect(payload.mechanical_seal_leak_de).toBe(false);
    expect(payload.mechanical_seal_leak_nde).toBe(false);
    expect(payload.pump_operating_state).toBe("STANDBY");
  });
});

import { describe, expect, it } from "vitest";
import {
  countRecordedMeasurements,
  emptyBulkCmonRow,
  toBulkAdHocPayload,
  toBulkAdHocPayloadRow,
  validateBulkCmonRows,
} from "./cmonBulkReading";

describe("cmonBulkReading", () => {
  it("emptyBulkCmonRow starts with every field blank/unselected", () => {
    const row = emptyBulkCmonRow("row-1");
    expect(row.selected).toBe(false);
    expect(row.pumpTag).toBe("");
    expect(row.readingDate).toBe("");
    expect(row.finding).toBe("");
    expect(row.measurements.mechsealTempDe).toBe("");
    expect(row.measurements.mechsealTempNde).toBe("");
    expect(row.measurements.leakDe).toBe("");
    expect(row.measurements.leakNde).toBe("");
  });

  it("validateBulkCmonRows: missing pump and missing reading date are errors", () => {
    const row = emptyBulkCmonRow("row-1");
    const { results, summary } = validateBulkCmonRows([row]);
    expect(results["row-1"].level).toBe("ERROR");
    expect(results["row-1"].errors).toContain("Pump is required.");
    expect(results["row-1"].errors).toContain("Reading Date is required.");
    expect(summary.errors).toBe(1);
    expect(summary.ready).toBe(0);
  });

  it("validateBulkCmonRows: unknown pump against the canonical set is an error", () => {
    const row = emptyBulkCmonRow("row-1", { pumpTag: "GHOST-PUMP", readingDate: "2026-09-06" });
    const { results } = validateBulkCmonRows([row], { canonicalPumpTags: new Set(["REAL-PUMP"]) });
    expect(results["row-1"].level).toBe("ERROR");
    expect(results["row-1"].errors[0]).toMatch(/Unknown pump/);
  });

  it("validateBulkCmonRows: a valid row is READY", () => {
    const row = emptyBulkCmonRow("row-1", { pumpTag: "REAL-PUMP", readingDate: "2026-09-06" });
    const { results, summary } = validateBulkCmonRows([row], { canonicalPumpTags: new Set(["REAL-PUMP"]) });
    expect(results["row-1"].level).toBe("READY");
    expect(summary.ready).toBe(1);
    expect(summary.errors).toBe(0);
  });

  it("validateBulkCmonRows: does NOT flag duplicate pump tags across rows as an error (no such backend rule exists)", () => {
    const rows = [
      emptyBulkCmonRow("row-1", { pumpTag: "REAL-PUMP", readingDate: "2026-09-06" }),
      emptyBulkCmonRow("row-2", { pumpTag: "REAL-PUMP", readingDate: "2026-09-06" }),
    ];
    const { summary } = validateBulkCmonRows(rows, { canonicalPumpTags: new Set(["REAL-PUMP"]) });
    expect(summary.errors).toBe(0);
    expect(summary.ready).toBe(2);
  });

  it("countRecordedMeasurements counts only non-blank fields", () => {
    const row = emptyBulkCmonRow("row-1");
    expect(countRecordedMeasurements(row.measurements)).toBe(0);
    row.measurements.mechsealTempDe = "75.2";
    row.measurements.leakDe = "false";
    expect(countRecordedMeasurements(row.measurements)).toBe(2);
  });

  it("toBulkAdHocPayloadRow: blank finding becomes null, not empty string", () => {
    const row = emptyBulkCmonRow("row-1", { pumpTag: "REAL-PUMP", readingDate: "2026-09-06", finding: "  " });
    const payloadRow = toBulkAdHocPayloadRow(row);
    expect(payloadRow.finding).toBeNull();
  });

  it("toBulkAdHocPayloadRow: DE-only, NDE-only, DE+NDE, and blank all preserved distinctly via the shared measurement builder", () => {
    const row = emptyBulkCmonRow("row-1", { pumpTag: "REAL-PUMP", readingDate: "2026-09-06" });
    row.measurements.mechsealTempDe = "75.2";
    row.measurements.flushingTempNde = "61.5";
    row.measurements.quenchTempDe = "60";
    row.measurements.quenchTempNde = "44";
    row.measurements.suctionPressure = "0";
    const payloadRow = toBulkAdHocPayloadRow(row);
    expect(payloadRow.measurements.mechseal_temp_de).toBe(75.2);
    expect(payloadRow.measurements.mechseal_temp_nde).toBeNull();
    expect(payloadRow.measurements.flushing_temp_de).toBeNull();
    expect(payloadRow.measurements.flushing_temp_nde).toBe(61.5);
    expect(payloadRow.measurements.quench_temp_de).toBe(60);
    expect(payloadRow.measurements.quench_temp_nde).toBe(44);
    expect(payloadRow.measurements.suction_pressure).toBe(0);
    expect(payloadRow.measurements.suction_pressure).not.toBeNull();
    expect(payloadRow.measurements.bearing_temp_de).toBeNull();
  });

  it("toBulkAdHocPayload builds the exact { readings: [...] } wire shape, one entry per row, in order", () => {
    const rows = [
      emptyBulkCmonRow("row-1", { pumpTag: "PUMP-A", readingDate: "2026-09-06" }),
      emptyBulkCmonRow("row-2", { pumpTag: "PUMP-B", readingDate: "2026-09-06" }),
    ];
    const payload = toBulkAdHocPayload(rows);
    expect(payload.readings).toHaveLength(2);
    expect(payload.readings[0].asset_code).toBe("PUMP-A");
    expect(payload.readings[1].asset_code).toBe("PUMP-B");
  });

  it("row isolation: mutating one row's measurements object never touches another row's", () => {
    const rowA = emptyBulkCmonRow("row-1", { pumpTag: "PUMP-A", readingDate: "2026-09-06" });
    const rowB = emptyBulkCmonRow("row-2", { pumpTag: "PUMP-B", readingDate: "2026-09-06" });
    rowA.measurements.mechsealTempDe = "75.2";
    expect(rowB.measurements.mechsealTempDe).toBe(""); // independent objects, no shared reference
  });
});

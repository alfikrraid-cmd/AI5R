import { describe, expect, it } from "vitest";
import {
  buildImportPreview,
  mapHeaders,
  normalizePumpTagCandidate,
  parseExcelDate,
  parseLeakCell,
  resolvePumpTag,
} from "./conditionMonitoringExcelImport";

const CANONICAL_PUMPS = new Set(["211-P-1A", "418-P-1"]);

function makeRowIdFactory() {
  let n = 0;
  return () => `import-row-${++n}`;
}

describe("conditionMonitoringExcelImport -- pump resolution", () => {
  it("EXACT_MATCH for an already-canonical tag", () => {
    expect(resolvePumpTag("211-P-1A", CANONICAL_PUMPS)).toEqual({ status: "EXACT_MATCH", assetCode: "211-P-1A" });
  });

  it("EXACT_MATCH is case/whitespace tolerant (pure typography, not an identity ambiguity)", () => {
    expect(resolvePumpTag("  211-p-1a  ", CANONICAL_PUMPS)).toEqual({ status: "EXACT_MATCH", assetCode: "211-P-1A" });
  });

  it("NORMALIZED_MATCH reconstructs the canonical hyphenated spelling", () => {
    expect(normalizePumpTagCandidate("211P1A")).toBe("211-P-1A");
    expect(resolvePumpTag("211P1A", CANONICAL_PUMPS)).toEqual({ status: "NORMALIZED_MATCH", assetCode: "211-P-1A" });
  });

  it("NOT_FOUND never invents a pump -- returns the raw trimmed value for the existing validator to flag", () => {
    expect(resolvePumpTag("GHOST-PUMP", CANONICAL_PUMPS)).toEqual({ status: "NOT_FOUND", assetCode: "GHOST-PUMP" });
  });
});

describe("conditionMonitoringExcelImport -- date parsing", () => {
  it("ISO date passes through", () => {
    expect(parseExcelDate("2026-09-06")).toEqual({ value: "2026-09-06", status: "OK" });
  });
  it("DD/MM/YYYY (day > 12) is unambiguous", () => {
    expect(parseExcelDate("25/12/2026")).toEqual({ value: "2026-12-25", status: "OK" });
  });
  it("ambiguous A/B/YYYY (both <= 12) is rejected, never guessed as MM/DD", () => {
    expect(parseExcelDate("09/10/26").status).toBe("AMBIGUOUS");
  });
  it("blank is BLANK, not an error", () => {
    expect(parseExcelDate("").status).toBe("BLANK");
  });
});

describe("conditionMonitoringExcelImport -- leak tri-state parsing (deterministic aliases)", () => {
  it("blank / Not Recorded -> null, never coerced to false", () => {
    expect(parseLeakCell("")).toEqual({ value: null, status: "OK" });
    expect(parseLeakCell("Not Recorded")).toEqual({ value: null, status: "OK" });
  });
  it("No Leak / false / No / 0 -> false", () => {
    for (const token of ["No Leak", "false", "No", "0"]) {
      expect(parseLeakCell(token)).toEqual({ value: false, status: "OK" });
    }
  });
  it("Leak Detected / true / Yes / 1 / Leak -> true", () => {
    for (const token of ["Leak Detected", "true", "Yes", "1", "Leak"]) {
      expect(parseLeakCell(token)).toEqual({ value: true, status: "OK" });
    }
  });
  it("an unrecognized token is an ERROR, never guessed", () => {
    expect(parseLeakCell("maybe")).toEqual({ value: null, status: "ERROR" });
  });
  it("NULL and FALSE remain distinct outcomes", () => {
    expect(parseLeakCell("").value).toBeNull();
    expect(parseLeakCell("No Leak").value).toBe(false);
    expect(parseLeakCell("").value).not.toBe(parseLeakCell("No Leak").value);
  });
});

describe("conditionMonitoringExcelImport -- header mapping", () => {
  it("Pump Tag is the only structurally required column", () => {
    const { missingRequiredFields } = mapHeaders(["Pump Tag *"]);
    expect(missingRequiredFields).toEqual([]);
  });
  it("a missing Pump Tag column is reported", () => {
    const { missingRequiredFields } = mapHeaders(["Reading Date *"]);
    expect(missingRequiredFields).toEqual(["pumpTag"]);
  });
  it("unrecognized columns are reported as unknown, not silently dropped", () => {
    const { unknownColumns } = mapHeaders(["Pump Tag *", "Some Random Column"]);
    expect(unknownColumns).toEqual(["Some Random Column"]);
  });
});

// MWO-LTSA-CMON-EXCEL-IMPORT-001, Section 9 -- the representative fixture
// workbook: 7 valid heterogeneous rows plus the required invalid cases.
describe("conditionMonitoringExcelImport -- Section 9 representative fixture", () => {
  const headers = [
    "Pump Tag *",
    "Reading Date *",
    "Mechanical Seal Temp DE",
    "Mechanical Seal Temp NDE",
    "Suction Pressure",
    "Mechanical Seal Leak DE",
    "Mechanical Seal Leak NDE",
    "Some Unknown Column",
  ];

  const rows = [
    ["211-P-1A", "2026-09-06", "75.2", "", "", "", "", ""], // Row 1: exact canonical pump, DE-only
    ["211p1a", "2026-09-06", "", "68.0", "", "", "", ""], // Row 2: normalized pump tag, NDE-only
    ["418-P-1", "2026-09-06", "70.0", "65.0", "", "", "", ""], // Row 3: DE + NDE
    ["211-P-1A", "2026-09-06", "", "", "0", "", "", ""], // Row 4: explicit numeric 0
    ["211-P-1A", "2026-09-06", "", "", "", "", "", ""], // Row 5: all measurements blank
    ["211-P-1A", "2026-09-06", "", "", "", "false", "", ""], // Row 6: Leak DE=false, NDE=null
    ["211-P-1A", "2026-09-06", "", "", "", "true", "false", ""], // Row 7: Leak DE=true, NDE=false
    ["GHOST-PUMP", "2026-09-06", "", "", "", "", "", ""], // invalid: unknown pump
    ["211-P-1A", "2026-09-06", "not-a-number", "", "", "", "", ""], // invalid: invalid numeric
    ["211-P-1A", "2026-09-06", "", "", "", "maybe", "", ""], // invalid: unknown leak token
    ["", "2026-09-06", "75.2", "", "", "", "", ""], // invalid: missing pump
  ];

  function preview() {
    return buildImportPreview({ headers, rows }, { canonicalPumpTags: CANONICAL_PUMPS, makeRowId: makeRowIdFactory() });
  }

  it("no row is silently discarded -- every data row produces a Bulk Editor row", () => {
    const result = preview();
    expect(result.structuralError).toBeNull();
    expect(result.rows).toHaveLength(rows.length);
  });

  it("Row 1: exact canonical pump, DE-only measurement preserved", () => {
    const row = preview().rows[0];
    expect(row.pumpTag).toBe("211-P-1A");
    expect(row.measurements.mechsealTempDe).toBe("75.2");
    expect(row.measurements.mechsealTempNde).toBe("");
    expect(row.importErrors).toEqual([]);
  });

  it("Row 2: normalized pump tag resolved, NDE-only measurement preserved", () => {
    const row = preview().rows[1];
    expect(row.pumpTag).toBe("211-P-1A"); // normalized from "211p1a"
    expect(row.measurements.mechsealTempDe).toBe("");
    expect(row.measurements.mechsealTempNde).toBe("68.0");
  });

  it("Row 3: DE + NDE both preserved independently", () => {
    const row = preview().rows[2];
    expect(row.measurements.mechsealTempDe).toBe("70.0");
    expect(row.measurements.mechsealTempNde).toBe("65.0");
  });

  it("Row 4: explicit numeric 0 preserved, never coerced to blank", () => {
    const row = preview().rows[3];
    expect(row.measurements.suctionPressure).toBe("0");
  });

  it("Row 5: all measurements blank stay blank -- nothing invented", () => {
    const row = preview().rows[4];
    expect(row.measurements.mechsealTempDe).toBe("");
    expect(row.measurements.suctionPressure).toBe("");
    expect(row.measurements.leakDe).toBe("");
  });

  it("Row 6: Leak DE=false, Leak NDE=not-recorded (blank), NULL != FALSE", () => {
    const row = preview().rows[5];
    expect(row.measurements.leakDe).toBe("false");
    expect(row.measurements.leakNde).toBe("");
  });

  it("Row 7: Leak DE=true, Leak NDE=false, independently preserved", () => {
    const row = preview().rows[6];
    expect(row.measurements.leakDe).toBe("true");
    expect(row.measurements.leakNde).toBe("false");
  });

  it("unknown pump row is retained with an import error, never dropped", () => {
    const row = preview().rows[7];
    expect(row.pumpTag).toBe("GHOST-PUMP"); // raw value retained for the existing validator to flag
    expect(row.importErrors.some((m) => m.includes("not found"))).toBe(true);
  });

  it("invalid numeric row is retained, value blanked, error reported", () => {
    const row = preview().rows[8];
    expect(row.measurements.mechsealTempDe).toBe(""); // never guessed/coerced
    expect(row.importErrors.some((m) => m.includes("not a valid number"))).toBe(true);
  });

  it("unknown leak token row is retained, value blanked, error reported", () => {
    const row = preview().rows[9];
    expect(row.measurements.leakDe).toBe("");
    expect(row.importErrors.some((m) => m.includes("not recognized"))).toBe(true);
  });

  it("missing pump row is retained -- pumpTag stays blank, caught by the existing validator, not silently dropped", () => {
    const row = preview().rows[10];
    expect(row.pumpTag).toBe("");
    expect(row).toBeTruthy(); // present in the row list, not discarded
  });

  it("unknown column produces a warning, not a structural failure", () => {
    const result = preview();
    expect(result.structuralError).toBeNull();
    expect(result.warnings.some((w) => w.includes("Some Unknown Column"))).toBe(true);
  });

  it("row source metadata is attached for Excel-imported rows", () => {
    const row = preview().rows[0];
    expect(row.source).toBe("EXCEL_IMPORT");
    expect(row.sourceRow).toBe(2); // header (row 1) + this being the first data row
  });

  it("row isolation: each row's measurements object is independent", () => {
    const result = preview();
    result.rows[0].measurements.mechsealTempDe = "MUTATED";
    expect(result.rows[2].measurements.mechsealTempDe).toBe("70.0"); // untouched
  });
});

describe("conditionMonitoringExcelImport -- overlong cell / structural cases", () => {
  it("missing Pump Tag column is a structural error -- no rows enter the Bulk Editor", () => {
    const result = buildImportPreview(
      { headers: ["Reading Date *"], rows: [["2026-09-06"]] },
      { canonicalPumpTags: CANONICAL_PUMPS, makeRowId: makeRowIdFactory() }
    );
    expect(result.structuralError).toMatch(/Pump Tag/);
    expect(result.rows).toBeUndefined();
  });

  it("more than MAX_IMPORT_ROWS rows is a structural error", () => {
    const manyRows = Array.from({ length: 1001 }, () => ["211-P-1A", "2026-09-06"]);
    const result = buildImportPreview(
      { headers: ["Pump Tag *", "Reading Date *"], rows: manyRows },
      { canonicalPumpTags: CANONICAL_PUMPS, makeRowId: makeRowIdFactory() }
    );
    expect(result.structuralError).toMatch(/1000/);
  });
});

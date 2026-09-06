import { describe, expect, it } from "vitest";
import {
  buildImportPreview,
  mapExcelRowToBulkRow,
  mapHeaders,
  normalizePumpTagCandidate,
  parseExcelDate,
  parseFrequency,
  parsePlannedActivities,
  resolvePumpTag,
} from "./pmExcelImport";
import { validateBulkRows } from "./pmBulkSchedule";

const PUMPS = new Set(["211-P-1A", "211-P-1B", "110-P-12B", "533-P-1"]);

let idCounter = 0;
function makeRowId() {
  idCounter += 1;
  return `import-row-${idCounter}`;
}

describe("mapHeaders -- Section E", () => {
  it("accepts canonical headers case-insensitively", () => {
    const { fieldToColumnIndex, missingRequiredFields } = mapHeaders(["PUMP TAG", "frequency", "Start Date"]);
    expect(fieldToColumnIndex).toEqual({ pumpTag: 0, frequency: 1, startDate: 2 });
    expect(missingRequiredFields).toEqual([]);
  });

  it("accepts every documented alias for each field", () => {
    const headers = ["Asset Code", "Interval", "Effective Date", "Activities", "Technician", "Duration Minutes", "Remarks"];
    const { fieldToColumnIndex } = mapHeaders(headers);
    expect(fieldToColumnIndex).toEqual({
      pumpTag: 0, frequency: 1, startDate: 2, plannedActivities: 3, technician: 4, duration: 5, notes: 6,
    });
  });

  it("reports unknown columns without blocking, and missing required columns as blocking", () => {
    const { unknownColumns, missingRequiredFields } = mapHeaders(["Pump Tag", "Some Random Column"]);
    expect(unknownColumns).toEqual(["Some Random Column"]);
    expect(missingRequiredFields).toEqual(["frequency", "startDate"]);
  });

  it("tolerates the template's own trailing asterisk on required headers", () => {
    const { fieldToColumnIndex } = mapHeaders(["Pump Tag *", "Frequency *", "Start Date *"]);
    expect(fieldToColumnIndex).toEqual({ pumpTag: 0, frequency: 1, startDate: 2 });
  });
});

describe("normalizePumpTagCandidate / resolvePumpTag -- Section F", () => {
  it("reconstructs the canonical hyphenated form from a compact tag (proven by the existing copilot normalizer)", () => {
    expect(normalizePumpTagCandidate("110P12B")).toBe("110-P-12B");
    expect(normalizePumpTagCandidate("110p12b")).toBe("110-P-12B");
    expect(normalizePumpTagCandidate("110-p12b")).toBe("110-P-12B");
  });

  it("classifies an exact canonical tag as EXACT_MATCH", () => {
    expect(resolvePumpTag("211-P-1A", PUMPS)).toEqual({ status: "EXACT_MATCH", assetCode: "211-P-1A" });
  });

  it("classifies whitespace/case-only differences as EXACT_MATCH", () => {
    expect(resolvePumpTag("  211-p-1a  ", PUMPS)).toEqual({ status: "EXACT_MATCH", assetCode: "211-P-1A" });
  });

  it("classifies a compact form that reconstructs to a real pump as NORMALIZED_MATCH", () => {
    expect(resolvePumpTag("110P12B", PUMPS)).toEqual({ status: "NORMALIZED_MATCH", assetCode: "110-P-12B" });
  });

  it("classifies an unresolvable tag as NOT_FOUND, preserving the raw value", () => {
    expect(resolvePumpTag("999-P-XYZ", PUMPS)).toEqual({ status: "NOT_FOUND", assetCode: "999-P-XYZ" });
  });

  it("never invents a pump: a syntactically-valid but non-canonical reconstruction is still NOT_FOUND", () => {
    expect(resolvePumpTag("999P99Z", PUMPS).status).toBe("NOT_FOUND");
  });
});

describe("parseFrequency -- Section G", () => {
  it.each([
    ["Daily", "DAILY"], ["daily", "DAILY"], ["Harian", "DAILY"],
    ["Weekly", "WEEKLY"], ["Mingguan", "WEEKLY"],
    ["Monthly", "MONTHLY"], ["Bulanan", "MONTHLY"],
    ["Runtime Based", "RUNTIME_BASED"], ["Runtime-Based", "RUNTIME_BASED"], ["Runtime", "RUNTIME_BASED"], ["Operating Hours", "RUNTIME_BASED"],
    ["MONTHLY", "MONTHLY"], ["monthly", "MONTHLY"],
  ])("maps %s -> %s", (raw, expected) => {
    expect(parseFrequency(raw)).toBe(expected);
  });

  it("returns null for an unrecognized frequency", () => {
    expect(parseFrequency("3 Monthly")).toBeNull();
    expect(parseFrequency("Quarterly")).toBeNull();
  });
});

describe("parseExcelDate -- Section H", () => {
  it("accepts a real Excel date cell / ISO string as-is", () => {
    expect(parseExcelDate("2026-10-01")).toEqual({ value: "2026-10-01", status: "OK" });
  });

  it("accepts an unambiguous DD/MM/YYYY (day > 12)", () => {
    expect(parseExcelDate("25/12/2026")).toEqual({ value: "2026-12-25", status: "OK" });
  });

  it("rejects an ambiguous D/M/YYYY where both numbers are <= 12", () => {
    expect(parseExcelDate("09/10/26")).toEqual({ value: null, status: "AMBIGUOUS" });
  });

  it("never silently guesses MM/DD/YYYY when only that reading is valid", () => {
    // 25 cannot be a month, so DD/MM/YYYY (12/25/2026) is invalid; MM/DD (Dec 25) is refused too.
    expect(parseExcelDate("12/25/2026").status).not.toBe("OK");
  });

  it("rejects a genuinely unparseable string", () => {
    expect(parseExcelDate("next month").status).toBe("INVALID");
  });

  it("treats a blank value as BLANK, not an error of its own", () => {
    expect(parseExcelDate("").status).toBe("BLANK");
  });
});

describe("parsePlannedActivities -- Section I", () => {
  it("treats blank Activities as valid, an empty selection", () => {
    expect(parsePlannedActivities("")).toEqual({ plannedMap: {}, unknownTokens: [] });
  });

  it("parses one activity", () => {
    expect(parsePlannedActivities("Flushing Line DE")).toEqual({
      plannedMap: { FLUSHING_LINE_DE: true },
      unknownTokens: [],
    });
  });

  it("parses multiple semicolon-separated activities, including General/DE/NDE for the same family independently", () => {
    const { plannedMap } = parsePlannedActivities("Flushing Line DE; Flushing Line NDE; Flushing Line General");
    expect(plannedMap).toEqual({
      FLUSHING_LINE_DE: true,
      FLUSHING_LINE_NDE: true,
      FLUSHING_LINE: true,
    });
  });

  it("accepts the catalog's own UI-description label form (\"... DE Side\")", () => {
    expect(parsePlannedActivities("Flushing Line DE Side").plannedMap).toEqual({ FLUSHING_LINE_DE: true });
  });

  it("keeps Cooler distinct from Cooling Water Cooler", () => {
    const { plannedMap } = parsePlannedActivities("Cooler DE; Cooling Water Cooler DE");
    expect(plannedMap).toEqual({ COOLER_DE: true, COOLING_WATER_COOLER_DE: true });
  });

  it("accepts Reservoir General as valid", () => {
    expect(parsePlannedActivities("Reservoir General").plannedMap).toEqual({ RESERVOIR: true });
    expect(parsePlannedActivities("Reservoir").plannedMap).toEqual({ RESERVOIR: true });
  });

  it("rejects Reservoir DE/NDE as unknown tokens (no such catalog code exists)", () => {
    const { plannedMap, unknownTokens } = parsePlannedActivities("Reservoir DE; Reservoir NDE");
    expect(plannedMap).toEqual({});
    expect(unknownTokens).toEqual(["Reservoir DE", "Reservoir NDE"]);
  });

  it("reports an unrecognized activity token individually", () => {
    const { unknownTokens } = parsePlannedActivities("Made Up Activity");
    expect(unknownTokens).toEqual(["Made Up Activity"]);
  });

  it("never accepts WCH or Water-Cooled Heat Exchanger as a valid token", () => {
    const { plannedMap, unknownTokens } = parsePlannedActivities("WCH; Water-Cooled Heat Exchanger DE");
    expect(plannedMap).toEqual({});
    expect(unknownTokens).toEqual(["WCH", "Water-Cooled Heat Exchanger DE"]);
  });
});

describe("mapExcelRowToBulkRow -- combined field mapping, Section K", () => {
  it("resolves a canonical pump, frequency alias, and real date into the exact bulk-row shape, with no done field and no legacy code", () => {
    const row = mapExcelRowToBulkRow(
      ["211-P-1A", "Harian", "2026-10-01", "Flushing Line DE", "Bagus Setiawan", "2.5", "Bring spare gasket"],
      { pumpTag: 0, frequency: 1, startDate: 2, plannedActivities: 3, technician: 4, duration: 5, notes: 6 },
      { canonicalPumpTags: PUMPS, rowNumber: 5, makeRowId }
    );
    expect(row.pumpTag).toBe("211-P-1A");
    expect(row.frequency).toBe("DAILY");
    expect(row.startDate).toBe("2026-10-01");
    expect(row.plannedMap).toEqual({ FLUSHING_LINE_DE: true });
    expect(row.technician).toBe("Bagus Setiawan");
    expect(row.duration).toBe("2.5");
    expect(row.notes).toBe("Bring spare gasket");
    expect(row.source).toBe("EXCEL_IMPORT");
    expect(row.sourceRow).toBe(5);
    expect(row.importErrors).toEqual([]);
    expect(row).not.toHaveProperty("done");
  });

  it("keeps an unresolvable pump's raw value so normal 4E.3 validation flags it as unknown", () => {
    const row = mapExcelRowToBulkRow(
      ["110-P-XYZ", "MONTHLY", "2026-10-01"],
      { pumpTag: 0, frequency: 1, startDate: 2 },
      { canonicalPumpTags: PUMPS, rowNumber: 4, makeRowId }
    );
    expect(row.pumpTag).toBe("110-P-XYZ");
    expect(row.importErrors).toEqual(['Pump "110-P-XYZ" not found.']);

    const { results } = validateBulkRows([row], { canonicalPumpTags: PUMPS });
    expect(results[row.id].level).toBe("ERROR");
    expect(results[row.id].errors[0]).toMatch(/Unknown pump/);
  });

  it("records an unsupported frequency as both the raw value (for live validation) and an import error", () => {
    const row = mapExcelRowToBulkRow(
      ["211-P-1A", "3 Monthly", "2026-10-01"],
      { pumpTag: 0, frequency: 1, startDate: 2 },
      { canonicalPumpTags: PUMPS, rowNumber: 8, makeRowId }
    );
    expect(row.frequency).toBe("3 Monthly");
    expect(row.importErrors).toContain('Frequency "3 Monthly" is unsupported.');
  });

  it("records an ambiguous date as an import error and leaves Start Date blank", () => {
    const row = mapExcelRowToBulkRow(
      ["211-P-1A", "MONTHLY", "09/10/26"],
      { pumpTag: 0, frequency: 1, startDate: 2 },
      { canonicalPumpTags: PUMPS, rowNumber: 12, makeRowId }
    );
    expect(row.startDate).toBe("");
    expect(row.importErrors).toContain('Start Date "09/10/26" is ambiguous.');
  });

  it("records an invalid activity token as an import error, e.g. Reservoir DE", () => {
    const row = mapExcelRowToBulkRow(
      ["211-P-1A", "MONTHLY", "2026-10-01", "Reservoir DE"],
      { pumpTag: 0, frequency: 1, startDate: 2, plannedActivities: 3 },
      { canonicalPumpTags: PUMPS, rowNumber: 17, makeRowId }
    );
    expect(row.importErrors).toContain('Activity "Reservoir DE" is invalid.');
    expect(row.plannedMap).toEqual({});
  });
});

describe("buildImportPreview -- Section J/L, structural gating", () => {
  function grid(headers, rows) {
    return { headers, rows };
  }

  it("blocks the import entirely when a required column is missing", () => {
    const preview = buildImportPreview(grid(["Pump Tag", "Frequency"], [["211-P-1A", "MONTHLY"]]), {
      canonicalPumpTags: PUMPS,
      makeRowId,
    });
    expect(preview.structuralError).toMatch(/Start Date/);
    expect(preview.rows).toBeUndefined();
  });

  it("rejects a file with more than 1000 rows", () => {
    const bigGrid = grid(["Pump Tag", "Frequency", "Start Date"], Array.from({ length: 1001 }, () => ["211-P-1A", "MONTHLY", "2026-10-01"]));
    const preview = buildImportPreview(bigGrid, { canonicalPumpTags: PUMPS, makeRowId });
    expect(preview.structuralError).toMatch(/1000/);
  });

  it("retains invalid rows for manual correction instead of discarding them", () => {
    const preview = buildImportPreview(
      grid(
        ["Pump Tag", "Frequency", "Start Date"],
        [
          ["211-P-1A", "MONTHLY", "2026-10-01"],
          ["999-P-XYZ", "MONTHLY", "2026-10-01"], // unknown pump -- must still produce a row
        ]
      ),
      { canonicalPumpTags: PUMPS, makeRowId }
    );
    expect(preview.structuralError).toBeNull();
    expect(preview.rows).toHaveLength(2);
    expect(preview.rows[1].pumpTag).toBe("999-P-XYZ");
  });

  it("warns (without blocking) about an unknown extra column", () => {
    const preview = buildImportPreview(
      grid(["Pump Tag", "Frequency", "Start Date", "Foo Bar"], [["211-P-1A", "MONTHLY", "2026-10-01", "ignored"]]),
      { canonicalPumpTags: PUMPS, makeRowId }
    );
    expect(preview.structuralError).toBeNull();
    expect(preview.warnings[0]).toMatch(/Foo Bar/);
    expect(preview.rows).toHaveLength(1);
  });

  it("detects duplicate raw rows via the existing 4E.3 key (asset_code + frequency + start date)", () => {
    const preview = buildImportPreview(
      grid(
        ["Pump Tag", "Frequency", "Start Date"],
        [
          ["211-P-1A", "MONTHLY", "2026-10-01"],
          ["211-P-1A", "MONTHLY", "2026-10-01"],
        ]
      ),
      { canonicalPumpTags: PUMPS, makeRowId }
    );
    const { results, summary } = validateBulkRows(preview.rows, { canonicalPumpTags: PUMPS });
    expect(summary.errors).toBe(1);
    expect(Object.values(results).some((r) => r.errors.some((m) => m.includes("Duplicate")))).toBe(true);
  });

  it("detects duplicates that only collide AFTER pump-tag normalization (110P12B vs 110-P-12B)", () => {
    const preview = buildImportPreview(
      grid(
        ["Pump Tag", "Frequency", "Start Date"],
        [
          ["110P12B", "MONTHLY", "2026-10-01"],
          ["110-P-12B", "MONTHLY", "2026-10-01"],
        ]
      ),
      { canonicalPumpTags: PUMPS, makeRowId }
    );
    expect(preview.rows[0].pumpTag).toBe("110-P-12B");
    expect(preview.rows[1].pumpTag).toBe("110-P-12B");
    const { summary } = validateBulkRows(preview.rows, { canonicalPumpTags: PUMPS });
    expect(summary.errors).toBe(1); // the two now-identical rows collide
  });
});

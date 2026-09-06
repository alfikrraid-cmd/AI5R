import { describe, expect, it } from "vitest";
import { buildImportPreview } from "./pmExcelImport";
import { validateBulkRows } from "./pmBulkSchedule";

// AI5R-PHASE4E5, Section G -- Excel end-to-end UAT, JS half. The grids
// below are exactly what CORE-SERVICES/API/TESTS/
// test_pm_schedule_excel_e2e_uat_4e5.py proved the REAL parse_xlsx_grid()
// produces for the same fixture workbook (same headers, same row values,
// same row order) -- this file proves the CLIENT-SIDE half of the
// mandatory flow (parsed grid -> mapped Bulk Editor rows -> validation)
// against that exact shape, closing the loop end to end without needing
// a Python/JS bridge in one test runner.
const TEMPLATE_HEADERS = ["Pump Tag *", "Frequency *", "Start Date *", "Planned Activities", "Assigned Technician", "Estimated Duration", "Notes"];

const CANONICAL_PUMP_TAGS = new Set(["211-P-1A", "211-P-1B", "110-P-12B"]);

let idCounter = 0;
function makeRowId() {
  idCounter += 1;
  return `uat-row-${idCounter}`;
}

describe("Section G UAT -- valid workbook end to end", () => {
  const grid = {
    headers: TEMPLATE_HEADERS,
    rows: [
      ["211-P-1A", "MONTHLY", "2026-11-01", "Flushing Line DE; Cooler DE; Cooling Water Cooler DE; Reservoir General", "Sari Wulandari", "2", "exact pump"],
      ["110P12B", "MONTHLY", "2026-11-01", "", "", "", "normalized pump"],
      ["211-P-1B", "Harian", "2026-11-02", "", "", "", "DAILY alias"],
      ["211-P-1B", "Mingguan", "2026-11-03", "", "", "", "WEEKLY alias"],
      ["211-P-1B", "Bulanan", "2026-11-04", "", "", "", "MONTHLY alias"],
      ["211-P-1B", "Runtime Based", "2026-11-05", "", "", "", "RUNTIME_BASED alias"],
    ],
  };

  it("maps every row into the SAME Bulk Editor row model, resolving pumps and frequency aliases correctly", () => {
    const preview = buildImportPreview(grid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });

    expect(preview.structuralError).toBeNull();
    expect(preview.rows).toHaveLength(6);

    const [exactRow, normalizedRow, dailyRow, weeklyRow, monthlyRow, runtimeRow] = preview.rows;

    expect(exactRow.pumpTag).toBe("211-P-1A");
    expect(exactRow.plannedMap).toEqual({
      FLUSHING_LINE_DE: true,
      COOLER_DE: true,
      COOLING_WATER_COOLER_DE: true,
      RESERVOIR: true,
    });
    expect(exactRow.importErrors).toEqual([]);

    expect(normalizedRow.pumpTag).toBe("110-P-12B"); // 110P12B resolved via the existing copilot normalizer
    expect(normalizedRow.importErrors).toEqual([]);

    expect(dailyRow.frequency).toBe("DAILY");
    expect(weeklyRow.frequency).toBe("WEEKLY");
    expect(monthlyRow.frequency).toBe("MONTHLY");
    expect(runtimeRow.frequency).toBe("RUNTIME_BASED");

    // Every imported row carries the mandatory-flow source metadata,
    // never persisted, only for display (Section K).
    for (const row of preview.rows) {
      expect(row.source).toBe("EXCEL_IMPORT");
      expect(typeof row.sourceRow).toBe("number");
    }
  });

  it("passes cleanly through the SAME validateBulkRows() the manual Bulk Editor uses, with zero errors", () => {
    const preview = buildImportPreview(grid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });
    const { summary } = validateBulkRows(preview.rows, { canonicalPumpTags: CANONICAL_PUMP_TAGS });

    expect(summary.rows).toBe(6);
    expect(summary.errors).toBe(0);
  });
});

describe("Section G UAT -- invalid workbook: every row retained for manual correction, none silently discarded", () => {
  const invalidGrid = {
    headers: TEMPLATE_HEADERS,
    rows: [
      ["999-P-XYZ", "MONTHLY", "2026-11-01", "", "", "", "unknown pump"],
      ["211-P-1A", "MONTHLY", "09/10/26", "", "", "", "ambiguous date"],
      ["211-P-1A", "3 Monthly", "2026-11-01", "", "", "", "invalid frequency"],
      ["211-P-1A", "MONTHLY", "2026-11-02", "Reservoir DE", "", "", "Reservoir DE"],
      ["211-P-1A", "MONTHLY", "2026-11-03", "Made Up Activity", "", "", "unknown activity"],
      ["110P12B", "MONTHLY", "2026-11-04", "", "", "", "duplicate-after-normalization row 1"],
      ["110-P-12B", "MONTHLY", "2026-11-04", "", "", "", "duplicate-after-normalization row 2"],
    ],
  };

  it("retains all 7 rows -- no structural error, no silent discard", () => {
    const preview = buildImportPreview(invalidGrid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });
    expect(preview.structuralError).toBeNull();
    expect(preview.rows).toHaveLength(7);
  });

  it("flags an unknown pump via the existing 4E.3 validation, using the raw value", () => {
    const preview = buildImportPreview(invalidGrid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });
    const { results } = validateBulkRows(preview.rows, { canonicalPumpTags: CANONICAL_PUMP_TAGS });
    expect(results[preview.rows[0].id].errors[0]).toMatch(/Unknown pump: 999-P-XYZ/);
  });

  it("flags an ambiguous date as an import error, never silently guessed", () => {
    const preview = buildImportPreview(invalidGrid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });
    expect(preview.rows[1].importErrors).toContain('Start Date "09/10/26" is ambiguous.');
    expect(preview.rows[1].startDate).toBe("");
  });

  it("flags an invalid frequency via the existing 4E.3 validation", () => {
    const preview = buildImportPreview(invalidGrid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });
    const { results } = validateBulkRows(preview.rows, { canonicalPumpTags: CANONICAL_PUMP_TAGS });
    expect(results[preview.rows[2].id].errors).toContain('Frequency "3 Monthly" is unsupported.');
  });

  it("flags Reservoir DE as an invalid activity token", () => {
    const preview = buildImportPreview(invalidGrid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });
    expect(preview.rows[3].importErrors).toContain('Activity "Reservoir DE" is invalid.');
    expect(preview.rows[3].plannedMap).toEqual({});
  });

  it("flags an unrecognized activity token", () => {
    const preview = buildImportPreview(invalidGrid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });
    expect(preview.rows[4].importErrors).toContain('Activity "Made Up Activity" is invalid.');
  });

  it("detects a duplicate that only collides AFTER pump normalization (110P12B vs 110-P-12B)", () => {
    const preview = buildImportPreview(invalidGrid, { canonicalPumpTags: CANONICAL_PUMP_TAGS, makeRowId });
    expect(preview.rows[5].pumpTag).toBe("110-P-12B");
    expect(preview.rows[6].pumpTag).toBe("110-P-12B");
    const { results, summary } = validateBulkRows(preview.rows, { canonicalPumpTags: CANONICAL_PUMP_TAGS });
    expect(summary.errors).toBeGreaterThanOrEqual(4); // unknown pump, invalid frequency, and the normalized duplicate all count
    expect(results[preview.rows[6].id].errors.some((m) => m.includes("Duplicate"))).toBe(true);
  });
});

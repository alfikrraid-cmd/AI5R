import { describe, expect, it } from "vitest";
import { computeBomColumns, resolveBomRowKey } from "./installationBomColumns";

describe("computeBomColumns", () => {
  it("returns [] for an empty or missing BOM", () => {
    expect(computeBomColumns([])).toEqual([]);
    expect(computeBomColumns(undefined)).toEqual([]);
  });

  it("SCAN-001-style (no/partName/qty/workRequired) keeps exactly those 4 columns, in known order", () => {
    const rows = [{ no: 1, partName: "Mating Ring", qty: 1, workRequired: "Replace" }];
    const columns = computeBomColumns(rows);
    expect(columns.map((c) => c.key)).toEqual(["no", "partName", "qty", "workRequired"]);
    expect(columns.find((c) => c.key === "partName").header).toBe("Part Name");
  });

  it("SCAN-002/003-style (item/drawingNumber/materialCode/description/material/qty/workRequired) surfaces every real column, none hidden", () => {
    const rows = [
      {
        item: 1,
        drawingNumber: "F 1250 443",
        materialCode: "9205",
        description: "Mating Ring",
        material: "Tungsten Carbide",
        qty: 1,
        workRequired: "Replace",
      },
    ];
    const columns = computeBomColumns(rows);
    expect(columns.map((c) => c.key)).toEqual([
      "item",
      "drawingNumber",
      "materialCode",
      "description",
      "material",
      "qty",
      "workRequired",
    ]);
  });

  it("does not include a column that is empty across every row", () => {
    const rows = [
      { item: 1, materialCode: null, description: "Mating Ring", qty: 1, workRequired: "Replace" },
      { item: 2, materialCode: "-", description: "Primary Ring", qty: 1, workRequired: "Replace" },
    ];
    // materialCode is genuinely absent (null) on row 1 but present on row 2 -- must still appear.
    const columns = computeBomColumns(rows);
    expect(columns.map((c) => c.key)).toContain("materialCode");
  });

  it("omits a column truly blank on every row (no value anywhere)", () => {
    const rows = [
      { item: 1, materialCode: null, description: "Mating Ring", qty: 1, workRequired: "Replace" },
      { item: 2, materialCode: "", description: "Primary Ring", qty: 1, workRequired: "Replace" },
    ];
    const columns = computeBomColumns(rows);
    expect(columns.map((c) => c.key)).not.toContain("materialCode");
  });

  it("appends unknown/unlisted keys after known columns with a humanized label, in first-seen order", () => {
    const rows = [{ item: 1, description: "Seat", qty: 1, workRequired: "Replace", customField: "X" }];
    const columns = computeBomColumns(rows);
    expect(columns[columns.length - 1]).toEqual({ key: "customField", header: "Custom Field" });
  });

  it("preserves the free-text disposition value verbatim as a plain column value (not an enum)", () => {
    // 702-P-2's real BOM row 12: "Clean, add Pin Mating Ring, and reuse".
    const rows = [{ no: 12, partName: "Gland Plate", qty: 1, workRequired: "Clean, add Pin Mating Ring, and reuse" }];
    const columns = computeBomColumns(rows);
    expect(columns.map((c) => c.key)).toContain("workRequired");
  });
});

describe("resolveBomRowKey", () => {
  it("uses 'no' when SCAN-001-style rows are present", () => {
    expect(resolveBomRowKey([{ no: 1 }, { no: 2 }])).toBe("no");
  });

  it("uses 'item' when SCAN-002-style rows are present", () => {
    expect(resolveBomRowKey([{ item: 1 }, { item: 2 }])).toBe("item");
  });

  it("defaults safely to 'no' for an empty/missing table", () => {
    expect(resolveBomRowKey([])).toBe("no");
    expect(resolveBomRowKey(undefined)).toBe("no");
  });
});

import { describe, expect, it } from "vitest";
import {
  PM_ACTIVITY_FAMILIES,
  PM_ACTIVITY_VARIANTS,
  buildActivitiesPayload,
  buildDoneMapFromActivities,
} from "./pmActivityCatalog";

// MWO-LTSA-PM-ACTIVITY-TAXONOMY-001

describe("PM_ACTIVITY_FAMILIES catalog", () => {
  it("has exactly the 7 Phase 4C-evidenced families, 19 total variants", () => {
    expect(PM_ACTIVITY_FAMILIES.map((f) => f.family)).toEqual([
      "Flushing Line",
      "Quench Line",
      "Strainer",
      "Check Valve",
      "Reservoir",
      "Cooler",
      "Cooling Water Cooler",
    ]);
    expect(PM_ACTIVITY_VARIANTS.length).toBe(19);
  });

  it("Reservoir has only a General variant -- no DE/NDE ever evidenced", () => {
    const reservoir = PM_ACTIVITY_FAMILIES.find((f) => f.family === "Reservoir");
    expect(reservoir.variants).toHaveLength(1);
    expect(reservoir.variants[0]).toMatchObject({ code: "RESERVOIR", side: null, label: "Reservoir" });
  });

  it('canonical future spelling is "Reservoir", never "Resevoir"', () => {
    const labels = PM_ACTIVITY_VARIANTS.map((v) => v.label);
    expect(labels).toContain("Reservoir");
    expect(labels).not.toContain("Resevoir");
  });

  it("Cooler display never says WCH or Water-Cooled Heat Exchanger", () => {
    const cooler = PM_ACTIVITY_FAMILIES.find((f) => f.family === "Cooler");
    expect(cooler.family).toBe("Cooler");
    for (const v of cooler.variants) {
      expect(v.label).not.toMatch(/WCH/i);
      expect(v.label).not.toMatch(/Water-Cooled Heat Exchanger/i);
    }
    expect(cooler.variants.map((v) => v.label)).toEqual(["Cooler", "Cooler DE Side", "Cooler NDE Side"]);
  });

  it("Cooler and Cooling Water Cooler are distinct families, never merged", () => {
    const families = PM_ACTIVITY_FAMILIES.map((f) => f.family);
    expect(families).toContain("Cooler");
    expect(families).toContain("Cooling Water Cooler");
    const coolerCodes = PM_ACTIVITY_FAMILIES.find((f) => f.family === "Cooler").variants.map((v) => v.code);
    const cwcCodes = PM_ACTIVITY_FAMILIES.find((f) => f.family === "Cooling Water Cooler").variants.map((v) => v.code);
    expect(coolerCodes.some((c) => cwcCodes.includes(c))).toBe(false);
  });

  it("every variant code is unique", () => {
    const codes = PM_ACTIVITY_VARIANTS.map((v) => v.code);
    expect(new Set(codes).size).toBe(codes.length);
  });

  it("legacy numeric codes are preserved exactly where they previously existed", () => {
    const byCode = Object.fromEntries(PM_ACTIVITY_VARIANTS.map((v) => [v.code, v]));
    expect(byCode.FLUSHING_LINE.legacyCode).toBe("1");
    expect(byCode.QUENCH_LINE.legacyCode).toBe("4");
    expect(byCode.STRAINER.legacyCode).toBe("19");
    expect(byCode.CHECK_VALVE_DE.legacyCode).toBe("17");
    expect(byCode.CHECK_VALVE_NDE.legacyCode).toBe("18");
    expect(byCode.RESERVOIR.legacyCode).toBe("6");
    expect(byCode.COOLING_WATER_COOLER.legacyCode).toBe("8");
    // new-only variants (never had a legacy number) carry null, never a
    // fabricated one.
    expect(byCode.FLUSHING_LINE_DE.legacyCode).toBeNull();
    expect(byCode.COOLER.legacyCode).toBeNull();
  });
});

describe("buildDoneMapFromActivities", () => {
  it("13: matches stable new string codes", () => {
    const map = buildDoneMapFromActivities([{ code: "COOLER_DE", description: "Cooler DE Side", side: "DE", done: true }]);
    expect(map.COOLER_DE).toBe(true);
    expect(map.COOLER).toBe(false);
    expect(map.COOLER_NDE).toBe(false);
  });

  it("14: matches pre-existing legacy numeric codes", () => {
    const map = buildDoneMapFromActivities([
      { code: "1", description: "Flushing Line", side: null, done: true },
      { code: "17", description: "Check Valve DE Side", side: "DE", done: true },
    ]);
    expect(map.FLUSHING_LINE).toBe(true);
    expect(map.CHECK_VALVE_DE).toBe(true);
    expect(map.CHECK_VALVE_NDE).toBe(false);
  });

  it("handles a mix of legacy and new codes on the same record", () => {
    const map = buildDoneMapFromActivities([
      { code: "1", description: "Flushing Line", done: true },
      { code: "COOLER_NDE", description: "Cooler NDE Side", side: "NDE", done: true },
    ]);
    expect(map.FLUSHING_LINE).toBe(true);
    expect(map.COOLER_NDE).toBe(true);
  });

  it("never matches by description text alone (historical-shaped entries produce an all-false map)", () => {
    // historical entries carry {description, done} with no code at all --
    // this function must never fall back to description matching (that
    // path is Phase 4B's own separate HistoricalActivitiesPerformed,
    // untouched here).
    const map = buildDoneMapFromActivities([{ description: "Flushing Line", done: true }]);
    expect(Object.values(map).every((v) => v === false)).toBe(true);
  });

  it("empty/missing activities produce an all-false map, never a crash", () => {
    expect(Object.values(buildDoneMapFromActivities(undefined)).every((v) => v === false)).toBe(true);
    expect(Object.values(buildDoneMapFromActivities([])).every((v) => v === false)).toBe(true);
  });
});

describe("buildActivitiesPayload", () => {
  it("13: serializes a selection with the new stable code, full description, and side", () => {
    const payload = buildActivitiesPayload({ COOLER_DE: true });
    const entry = payload.find((e) => e.code === "COOLER_DE");
    expect(entry).toEqual({ code: "COOLER_DE", description: "Cooler DE Side", side: "DE", done: true });
  });

  it("includes all 19 variants every time (preserves the existing full-catalog payload contract), unselected ones done=false", () => {
    const payload = buildActivitiesPayload({});
    expect(payload).toHaveLength(19);
    expect(payload.every((e) => e.done === false)).toBe(true);
  });

  it("General, DE, and NDE for the same family serialize independently", () => {
    const payload = buildActivitiesPayload({ COOLER: true, COOLER_DE: true, COOLER_NDE: true });
    const cooler = payload.filter((e) => e.code.startsWith("COOLER") && !e.code.startsWith("COOLING_WATER"));
    expect(cooler.filter((e) => e.done)).toHaveLength(3);
  });
});

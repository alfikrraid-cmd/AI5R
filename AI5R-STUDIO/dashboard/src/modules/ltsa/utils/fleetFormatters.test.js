import { describe, expect, it } from "vitest";
import { UNAVAILABLE, formatDays, formatHours, formatPercent, formatScore } from "./fleetFormatters";

// MWO-LTSA-040A -- extracted from the identical, duplicated formatter set
// FleetReliabilityPanel.jsx (037D) and FleetPowerBIPanel.jsx (038B) each
// independently defined -- one shared source, no third copy.

describe("fleetFormatters", () => {
  it("formatScore rounds to the nearest integer", () => {
    expect(formatScore(86.5)).toBe("87");
    expect(formatScore(0)).toBe("0");
  });

  it("formatScore returns Unavailable for null/undefined, never a fabricated number", () => {
    expect(formatScore(null)).toBe(UNAVAILABLE);
    expect(formatScore(undefined)).toBe(UNAVAILABLE);
  });

  it("formatDays rounds and appends 'days'", () => {
    expect(formatDays(42.3)).toBe("42 days");
  });

  it("formatDays returns Unavailable for null/undefined", () => {
    expect(formatDays(null)).toBe(UNAVAILABLE);
  });

  it("formatHours rounds and appends 'hrs'", () => {
    expect(formatHours(6.25)).toBe("6 hrs");
  });

  it("formatHours returns Unavailable for null/undefined", () => {
    expect(formatHours(null)).toBe(UNAVAILABLE);
  });

  it("formatPercent appends '%' without rounding", () => {
    expect(formatPercent(98.76)).toBe("98.76%");
  });

  it("formatPercent returns Unavailable for null/undefined", () => {
    expect(formatPercent(null)).toBe(UNAVAILABLE);
  });
});

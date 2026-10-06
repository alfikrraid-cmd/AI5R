import { describe, expect, it } from "vitest";
import { formatAreaScopeDisplay } from "./areaScopeDisplay";

describe("formatAreaScopeDisplay", () => {
  it("formats explicit ALL scope as 'All Areas'", () => {
    expect(formatAreaScopeDisplay("ALL", null)).toBe("All Areas");
    expect(formatAreaScopeDisplay("ALL", "")).toBe("All Areas");
    expect(formatAreaScopeDisplay("ALL", "ALL")).toBe("All Areas");
  });

  it("formats AREA scope with valid value", () => {
    expect(formatAreaScopeDisplay("AREA", "AREA-01")).toBe("AREA-01");
    expect(formatAreaScopeDisplay("AREA", "CDU-II")).toBe("CDU-II");
  });

  it("formats MA scope with valid value", () => {
    expect(formatAreaScopeDisplay("MA", "MA-01")).toBe("MA-01");
    expect(formatAreaScopeDisplay("MA", "KILANG-2")).toBe("KILANG-2");
  });

  it("never formats null or empty scope as 'All Areas'", () => {
    expect(formatAreaScopeDisplay(null, null)).toBe("No Area Access / Not Assigned");
    expect(formatAreaScopeDisplay(undefined, undefined)).toBe("No Area Access / Not Assigned");
    expect(formatAreaScopeDisplay("", "")).toBe("No Area Access / Not Assigned");
  });

  it("handles AREA or MA with missing or whitespace value safely", () => {
    expect(formatAreaScopeDisplay("AREA", null)).toBe("No Area Access / Not Assigned");
    expect(formatAreaScopeDisplay("AREA", "")).toBe("No Area Access / Not Assigned");
    expect(formatAreaScopeDisplay("AREA", "   ")).toBe("No Area Access / Not Assigned");
    expect(formatAreaScopeDisplay("MA", null)).toBe("No Area Access / Not Assigned");
    expect(formatAreaScopeDisplay("MA", "")).toBe("No Area Access / Not Assigned");
  });

  it("handles unknown data scope type safely", () => {
    expect(formatAreaScopeDisplay("UNKNOWN", "VAL")).toBe("No Area Access / Not Assigned");
  });
});

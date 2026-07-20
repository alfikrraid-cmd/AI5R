import { describe, expect, it } from "vitest";
import colors from "../../../design-system/theme/colors";
import { criticalityBadgeVariant, healthScoreColor, statusBadgeVariant } from "./pumpHealth";

describe("healthScoreColor", () => {
  it("returns success for a healthy score", () => {
    expect(healthScoreColor(92)).toBe(colors.success);
  });

  it("returns warning for a fair score", () => {
    expect(healthScoreColor(65)).toBe(colors.warning);
  });

  it("returns danger for a poor score", () => {
    expect(healthScoreColor(30)).toBe(colors.danger);
  });
});

describe("statusBadgeVariant", () => {
  it("maps every known status to its badge variant", () => {
    expect(statusBadgeVariant("RUNNING")).toBe("success");
    expect(statusBadgeVariant("STANDBY")).toBe("info");
    expect(statusBadgeVariant("MAINTENANCE")).toBe("warning");
    expect(statusBadgeVariant("FAULT")).toBe("danger");
  });

  it("falls back to purple for an unknown status", () => {
    expect(statusBadgeVariant("UNKNOWN")).toBe("purple");
  });
});

describe("criticalityBadgeVariant", () => {
  it("maps every known criticality to its badge variant", () => {
    expect(criticalityBadgeVariant("HIGH")).toBe("danger");
    expect(criticalityBadgeVariant("MEDIUM")).toBe("warning");
    expect(criticalityBadgeVariant("LOW")).toBe("info");
  });

  it("falls back to purple for an unknown criticality", () => {
    expect(criticalityBadgeVariant("UNKNOWN")).toBe("purple");
  });
});

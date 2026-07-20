import { describe, expect, it } from "vitest";
import {
  frequencyBadgeVariant,
  frequencyLabel,
  statusBadgeVariant,
  triggerTypeLabel,
} from "./pmStatus";

describe("statusBadgeVariant", () => {
  it("maps every closed-set status to a badge variant", () => {
    expect(statusBadgeVariant("ACTIVE")).toBe("success");
    expect(statusBadgeVariant("DUE_SOON")).toBe("warning");
    expect(statusBadgeVariant("OVERDUE")).toBe("danger");
    expect(statusBadgeVariant("ON_HOLD")).toBe("purple");
  });

  it("falls back to purple for an unknown status", () => {
    expect(statusBadgeVariant("UNKNOWN")).toBe("purple");
  });
});

describe("frequencyBadgeVariant", () => {
  it("maps every closed-set frequency to a badge variant", () => {
    expect(frequencyBadgeVariant("DAILY")).toBe("info");
    expect(frequencyBadgeVariant("WEEKLY")).toBe("info");
    expect(frequencyBadgeVariant("MONTHLY")).toBe("info");
    expect(frequencyBadgeVariant("RUNTIME_BASED")).toBe("purple");
  });

  it("falls back to purple for an unknown frequency", () => {
    expect(frequencyBadgeVariant("UNKNOWN")).toBe("purple");
  });
});

describe("frequencyLabel", () => {
  it("maps every closed-set frequency to a human-readable label", () => {
    expect(frequencyLabel("DAILY")).toBe("Daily");
    expect(frequencyLabel("WEEKLY")).toBe("Weekly");
    expect(frequencyLabel("MONTHLY")).toBe("Monthly");
    expect(frequencyLabel("RUNTIME_BASED")).toBe("Runtime-based");
  });

  it("falls back to the raw value for an unknown frequency", () => {
    expect(frequencyLabel("UNKNOWN")).toBe("UNKNOWN");
  });
});

describe("triggerTypeLabel", () => {
  it("maps every closed-set trigger type to a human-readable label", () => {
    expect(triggerTypeLabel("CALENDAR")).toBe("Calendar");
    expect(triggerTypeLabel("METER")).toBe("Runtime Meter");
  });

  it("falls back to the raw value for an unknown trigger type", () => {
    expect(triggerTypeLabel("UNKNOWN")).toBe("UNKNOWN");
  });
});

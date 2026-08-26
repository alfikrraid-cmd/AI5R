import { describe, expect, it } from "vitest";
import {
  frequencyBadgeVariant,
  frequencyLabel,
  statusBadgeVariant,
  statusLabel,
  triggerTypeLabel,
} from "./pmStatus";

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- owner-approved
// PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED lifecycle. DUE_SOON is
// removed (superseded, not renamed -- never part of the owner's approved
// vocabulary). ON_HOLD remains supported: a pre-existing stored value
// outside this MWO's own 5 states.
describe("statusBadgeVariant", () => {
  it("maps every closed-set status to a badge variant", () => {
    expect(statusBadgeVariant("PLANNED")).toBe("info");
    expect(statusBadgeVariant("ACTIVE")).toBe("success");
    expect(statusBadgeVariant("OVERDUE")).toBe("danger");
    expect(statusBadgeVariant("COMPLETED")).toBe("purple");
    expect(statusBadgeVariant("CANCELLED")).toBe("warning");
    expect(statusBadgeVariant("ON_HOLD")).toBe("purple");
  });

  it("falls back to purple for an unknown status", () => {
    expect(statusBadgeVariant("UNKNOWN")).toBe("purple");
  });
});

describe("statusLabel", () => {
  it("maps every closed-set status to a human-readable label", () => {
    expect(statusLabel("PLANNED")).toBe("Planned");
    expect(statusLabel("ACTIVE")).toBe("Active");
    expect(statusLabel("OVERDUE")).toBe("Overdue");
    expect(statusLabel("COMPLETED")).toBe("Completed");
    expect(statusLabel("CANCELLED")).toBe("Cancelled");
    expect(statusLabel("ON_HOLD")).toBe("On Hold");
  });

  it("falls back to the raw value for an unknown status", () => {
    expect(statusLabel("UNKNOWN")).toBe("UNKNOWN");
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

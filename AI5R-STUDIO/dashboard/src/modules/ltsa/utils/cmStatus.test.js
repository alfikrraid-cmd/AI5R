import { describe, expect, it } from "vitest";
import {
  failureCategoryLabel,
  priorityBadgeVariant,
  severityBadgeVariant,
  statusBadgeVariant,
} from "./cmStatus";

describe("statusBadgeVariant", () => {
  it("maps every closed-set status to a badge variant", () => {
    expect(statusBadgeVariant("OPEN")).toBe("danger");
    expect(statusBadgeVariant("IN_PROGRESS")).toBe("warning");
    expect(statusBadgeVariant("RESOLVED")).toBe("info");
    expect(statusBadgeVariant("CLOSED")).toBe("success");
  });

  it("falls back to purple for an unknown status", () => {
    expect(statusBadgeVariant("UNKNOWN")).toBe("purple");
  });
});

describe("severityBadgeVariant", () => {
  it("maps every closed-set severity to a badge variant", () => {
    expect(severityBadgeVariant("MINOR")).toBe("success");
    expect(severityBadgeVariant("MODERATE")).toBe("info");
    expect(severityBadgeVariant("MAJOR")).toBe("warning");
    expect(severityBadgeVariant("CRITICAL")).toBe("danger");
  });

  it("falls back to purple for an unknown severity", () => {
    expect(severityBadgeVariant("UNKNOWN")).toBe("purple");
  });
});

describe("priorityBadgeVariant", () => {
  it("maps every closed-set priority to a badge variant", () => {
    expect(priorityBadgeVariant("CRITICAL")).toBe("danger");
    expect(priorityBadgeVariant("HIGH")).toBe("warning");
    expect(priorityBadgeVariant("MEDIUM")).toBe("info");
    expect(priorityBadgeVariant("LOW")).toBe("success");
  });

  it("falls back to purple for an unknown priority", () => {
    expect(priorityBadgeVariant("UNKNOWN")).toBe("purple");
  });
});

describe("failureCategoryLabel", () => {
  it("maps every closed-set failure category to a human-readable label", () => {
    expect(failureCategoryLabel("MECHANICAL")).toBe("Mechanical");
    expect(failureCategoryLabel("ELECTRICAL")).toBe("Electrical");
    expect(failureCategoryLabel("SEAL_FAILURE")).toBe("Seal Failure");
    expect(failureCategoryLabel("INSTRUMENTATION")).toBe("Instrumentation");
    expect(failureCategoryLabel("PROCESS")).toBe("Process");
  });

  it("falls back to the raw value for an unknown category", () => {
    expect(failureCategoryLabel("UNKNOWN")).toBe("UNKNOWN");
  });
});

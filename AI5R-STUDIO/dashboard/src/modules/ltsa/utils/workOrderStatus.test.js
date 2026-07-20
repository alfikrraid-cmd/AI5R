import { describe, expect, it } from "vitest";
import { priorityBadgeVariant, statusBadgeVariant } from "./workOrderStatus";

describe("statusBadgeVariant", () => {
  it("maps every closed-set status to a badge variant", () => {
    expect(statusBadgeVariant("OPEN")).toBe("info");
    expect(statusBadgeVariant("IN_PROGRESS")).toBe("warning");
    expect(statusBadgeVariant("ON_HOLD")).toBe("purple");
    expect(statusBadgeVariant("COMPLETED")).toBe("success");
  });

  it("falls back to purple for an unknown status", () => {
    expect(statusBadgeVariant("UNKNOWN")).toBe("purple");
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

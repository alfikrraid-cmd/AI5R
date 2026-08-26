import { describe, expect, it } from "vitest";
import { isUnscheduledPlaceholder, mapConditionMonitoringScheduleRecord } from "./conditionMonitoringMapping";

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- pure-function coverage for
// the owner-approved PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED lifecycle
// applied to Condition Monitoring (migration 029), mirroring
// pmMapping.scheduleLifecycle.test.js's own identical PM coverage exactly.

function statusFor(rawStatus, nextDue) {
  return mapConditionMonitoringScheduleRecord({
    condition_monitoring_schedule_code: "CMS-1",
    status: rawStatus,
    next_due: nextDue,
  }).status;
}

describe("Condition Monitoring schedule lifecycle status", () => {
  it("is PLANNED when next_due falls in a future calendar month", () => {
    const today = new Date();
    const futureMonth = new Date(today.getFullYear(), today.getMonth() + 2, 15);
    expect(statusFor("ACTIVE", futureMonth.toISOString().slice(0, 10))).toBe("PLANNED");
  });

  it("is ACTIVE when next_due is today (current month, not yet passed)", () => {
    const today = new Date();
    expect(statusFor("ACTIVE", today.toISOString().slice(0, 10))).toBe("ACTIVE");
  });

  it("is OVERDUE when next_due has passed with no completion recorded", () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    expect(statusFor("ACTIVE", yesterday.toISOString().slice(0, 10))).toBe("OVERDUE");
  });

  it("never reports OVERDUE for a schedule already COMPLETED, regardless of an expired next_due", () => {
    expect(statusFor("COMPLETED", "2020-01-01")).toBe("COMPLETED");
  });

  it("never reports OVERDUE for a schedule already CANCELLED, regardless of an expired next_due", () => {
    expect(statusFor("CANCELLED", "2020-01-01")).toBe("CANCELLED");
  });

  it("completing an actual reading (status=COMPLETED) after the schedule was OVERDUE resolves to COMPLETED, not OVERDUE", () => {
    // Simulates the real transition: an ACTIVE schedule became OVERDUE
    // (next_due in the past), then an actual reading was recorded and the
    // atomic backend transition set status=COMPLETED. The stored
    // COMPLETED value must win over the still-expired next_due.
    expect(statusFor("COMPLETED", "2020-01-01")).toBe("COMPLETED");
  });
});

describe("isUnscheduledPlaceholder (Condition Monitoring)", () => {
  it("recognizes the historical-import UNSCHEDULED::<workbook> placeholder", () => {
    expect(isUnscheduledPlaceholder("UNSCHEDULED::CM & PM Summary HOC JUNI.xlsx")).toBe(true);
  });

  it("does not flag a real condition_monitoring_schedule_code as unscheduled", () => {
    expect(isUnscheduledPlaceholder("CMS-2001")).toBe(false);
  });
});

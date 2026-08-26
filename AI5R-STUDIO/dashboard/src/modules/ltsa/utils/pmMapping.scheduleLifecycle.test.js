import { describe, expect, it } from "vitest";
import { isUnscheduledPlaceholder, mapPMScheduleRecord, nextMonthFirstDay } from "./pmMapping";

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- pure-function coverage for
// the owner-approved PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED lifecycle,
// the next-month schedule-creation default, and the UNSCHEDULED::<workbook>
// presentation guard. No component rendering needed -- computeDisplayStatus/
// nextMonthFirstDay/isUnscheduledPlaceholder are all pure and exported (the
// first indirectly via mapPMScheduleRecord's own `status` field).

function statusFor(rawStatus, nextDue) {
  return mapPMScheduleRecord({ pm_schedule_code: "PMS-1", status: rawStatus, next_due: nextDue }).status;
}

describe("PM schedule lifecycle status", () => {
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
    const longExpired = "2020-01-01";
    expect(statusFor("COMPLETED", longExpired)).toBe("COMPLETED");
  });

  it("never reports OVERDUE for a schedule already CANCELLED, regardless of an expired next_due", () => {
    const longExpired = "2020-01-01";
    expect(statusFor("CANCELLED", longExpired)).toBe("CANCELLED");
  });

  it("passes a non-ACTIVE, non-terminal stored status (e.g. ON_HOLD) through unchanged", () => {
    expect(statusFor("ON_HOLD", "2020-01-01")).toBe("ON_HOLD");
  });
});

describe("nextMonthFirstDay", () => {
  it("derives the 1st of next calendar month from the given reference date, never a hard-coded month", () => {
    expect(nextMonthFirstDay(new Date(2026, 7, 15))).toBe("2026-09-01"); // August 2026 -> September
  });

  it("rolls over the year boundary correctly", () => {
    expect(nextMonthFirstDay(new Date(2026, 11, 20))).toBe("2027-01-01"); // December 2026 -> January 2027
  });
});

describe("isUnscheduledPlaceholder", () => {
  it("recognizes the historical-import UNSCHEDULED::<workbook> placeholder", () => {
    expect(isUnscheduledPlaceholder("UNSCHEDULED::Laporan PM, CM & Pemasangan Seal HCC JANUARI 2026.xlsx")).toBe(true);
  });

  it("does not flag a real pm_schedule_code as unscheduled", () => {
    expect(isUnscheduledPlaceholder("PMS-2001")).toBe(false);
  });

  it("does not flag null/undefined", () => {
    expect(isUnscheduledPlaceholder(null)).toBe(false);
    expect(isUnscheduledPlaceholder(undefined)).toBe(false);
  });
});

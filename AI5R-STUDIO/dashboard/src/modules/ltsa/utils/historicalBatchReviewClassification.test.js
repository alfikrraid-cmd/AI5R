import { describe, expect, it } from "vitest";
import { classifyPMOccurrence, classifyConditionMonitoringReading } from "./historicalBatchReviewClassification";

// MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- deterministic evidence
// classification, mirroring MWO-018's own exact criteria.

function pm(overrides = {}) {
  return {
    provenance: "HISTORICAL_IMPORT", workflowStatus: "DRAFT",
    equipmentTag: "211-P-18A", occurrenceDate: "2026-07-05", status: "DONE",
    activities: [{ code: "1", done: true }],
    ...overrides,
  };
}

function cmon(overrides = {}) {
  return {
    provenance: "HISTORICAL_IMPORT", workflowStatus: "DRAFT",
    equipmentTag: "220-P-4A", readingDate: "2026-07-01",
    mechsealTempDe: 70,
    ...overrides,
  };
}

describe("classifyPMOccurrence", () => {
  it("is READY_FOR_REVIEW when pump/date/status/activities are all present", () => {
    expect(classifyPMOccurrence(pm())).toBe("READY_FOR_REVIEW");
  });

  it("is NEEDS_ATTENTION when activities is empty", () => {
    expect(classifyPMOccurrence(pm({ activities: [] }))).toBe("NEEDS_ATTENTION");
  });

  it("is NEEDS_ATTENTION when status is not DONE", () => {
    expect(classifyPMOccurrence(pm({ status: null }))).toBe("NEEDS_ATTENTION");
  });

  it("returns null (not in the review queue) for a non-historical-import record", () => {
    expect(classifyPMOccurrence(pm({ provenance: "MANUAL" }))).toBeNull();
  });

  it("returns null for a record that is no longer DRAFT", () => {
    expect(classifyPMOccurrence(pm({ workflowStatus: "SUBMITTED" }))).toBeNull();
  });
});

describe("classifyConditionMonitoringReading", () => {
  it("is READY_FOR_REVIEW when pump/date and at least one measurement are present", () => {
    expect(classifyConditionMonitoringReading(cmon())).toBe("READY_FOR_REVIEW");
  });

  it("is NEEDS_ATTENTION when no measurement field is populated", () => {
    expect(classifyConditionMonitoringReading(cmon({ mechsealTempDe: null }))).toBe("NEEDS_ATTENTION");
  });

  it("returns null for a non-historical-import record", () => {
    expect(classifyConditionMonitoringReading(cmon({ provenance: "MANUAL" }))).toBeNull();
  });

  it("returns null for a record that is no longer DRAFT", () => {
    expect(classifyConditionMonitoringReading(cmon({ workflowStatus: "FINALIZED" }))).toBeNull();
  });
});

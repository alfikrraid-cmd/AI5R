import { describe, expect, it } from "vitest";
import {
  buildAssetEventStream,
  buildAssetSummary,
  buildAssetTimeline,
  buildPlantTimeline,
  eventStatusBadgeVariant,
  eventStatusLabel,
  eventTypeBadgeVariant,
  eventTypeLabel,
  filterStatusLabel,
  findAssetByTag,
  isOpenWorkOrderStatus,
  listAssets,
  mapConditionMonitoringReadingToEvent,
  mapMaintenanceHistoryToEvent,
  mapPMOccurrenceToEvent,
} from "./maintenanceHistory";

describe("legacy timeline helpers", () => {
  it("do not expose frontend sample assets or timelines at runtime", () => {
    expect(listAssets()).toEqual([]);
    expect(findAssetByTag("211-P-1A")).toBeNull();
    expect(buildAssetTimeline("211-P-1A")).toEqual([]);
    expect(buildPlantTimeline()).toEqual([]);
  });

  it("does not attach sample metadata to a real production pump tag", () => {
    const summary = buildAssetSummary({ tag: "211-P-1A", name: "FRESH FEED CHARGE PUMP", area: "REAKTOR" });

    expect(summary.pump).toBe("FRESH FEED CHARGE PUMP");
    expect(summary.tag).toBe("211-P-1A");
    expect(summary.area).toBe("REAKTOR");
    expect(summary.pump).not.toContain("Boiler Feedwater");
  });
});

describe("eventTypeBadgeVariant / eventTypeLabel", () => {
  it("maps every event type to a badge variant and label", () => {
    expect(eventTypeBadgeVariant("PM")).toBe("info");
    expect(eventTypeBadgeVariant("CM")).toBe("warning");
    expect(eventTypeBadgeVariant("WO")).toBe("purple");

    expect(eventTypeLabel("PM")).toBe("PM");
    expect(eventTypeLabel("CM")).toBe("CM");
    expect(eventTypeLabel("WO")).toBe("Work Order");
  });
});

describe("eventStatusBadgeVariant / eventStatusLabel", () => {
  it("dispatches to the correct per-type status helper", () => {
    const pmEvent = { type: "PM", status: "OVERDUE" };
    const cmEvent = { type: "CM", status: "OPEN" };
    const woEvent = { type: "WO", status: "IN_PROGRESS" };

    expect(eventStatusBadgeVariant(pmEvent)).toBe("danger");
    expect(eventStatusLabel(pmEvent)).toBe("Overdue");

    expect(eventStatusBadgeVariant(cmEvent)).toBe("danger");
    expect(eventStatusLabel(cmEvent)).toBe("Open");

    expect(eventStatusBadgeVariant(woEvent)).toBe("warning");
    expect(eventStatusLabel(woEvent)).toBe("In Progress");
  });
});

describe("filterStatusLabel", () => {
  it("humanizes statuses and falls back to raw unknowns", () => {
    expect(filterStatusLabel("ON_HOLD")).toBe("On Hold");
    expect(filterStatusLabel("DUE_SOON")).toBe("Due Soon");
    expect(filterStatusLabel("RESOLVED")).toBe("Resolved");
    expect(filterStatusLabel("COMPLETED")).toBe("Completed");
    expect(filterStatusLabel("UNKNOWN")).toBe("UNKNOWN");
  });
});

describe("isOpenWorkOrderStatus", () => {
  it("treats OPEN, IN_PROGRESS, and ON_HOLD as open", () => {
    expect(isOpenWorkOrderStatus("OPEN")).toBe(true);
    expect(isOpenWorkOrderStatus("IN_PROGRESS")).toBe(true);
    expect(isOpenWorkOrderStatus("ON_HOLD")).toBe(true);
    expect(isOpenWorkOrderStatus("COMPLETED")).toBe(false);
  });
});

describe("real API-backed asset event stream", () => {
  it("merges only matching production asset events without sample fallback", () => {
    const events = [
      mapMaintenanceHistoryToEvent({ maintenance_record_code: "MH-1", asset_code: "211-P-1A", performed_at: "2026-08-02", action_taken: "Checked", performed_by: "Engineer" }),
      mapPMOccurrenceToEvent({ pm_occurrence_code: "PM-OCC-1", asset_code: "220-P-4A", occurrence_date: "2026-08-03", checklist_completion: [] }),
      mapConditionMonitoringReadingToEvent({ condition_monitoring_reading_code: "CMON-1", asset_code: "211-P-1A", reading_date: "2026-08-04" }),
    ];

    expect(buildAssetEventStream(events, "211-P-1A").map((event) => event.id)).toEqual(["CMON-1", "MH-1"]);
  });
});

import { describe, expect, it } from "vitest";
import {
  buildAssetSummary,
  buildAssetTimeline,
  eventStatusBadgeVariant,
  eventStatusLabel,
  eventTypeBadgeVariant,
  eventTypeLabel,
  filterStatusLabel,
  findAssetByTag,
  listAssets,
} from "./maintenanceHistory";

describe("listAssets / findAssetByTag", () => {
  it("lists every sample pump sorted by tag", () => {
    const assets = listAssets();

    expect(assets.length).toBeGreaterThan(0);
    const tags = assets.map((asset) => asset.tag);
    expect([...tags].sort()).toEqual(tags);
  });

  it("finds an asset by tag", () => {
    const asset = findAssetByTag("641-P-5");

    expect(asset?.code).toBe("PMP-009");
  });

  it("returns null for an unknown tag", () => {
    expect(findAssetByTag("NO-SUCH-TAG")).toBeNull();
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
  it("humanizes a status shared across modules the same way regardless of source", () => {
    expect(filterStatusLabel("ON_HOLD")).toBe("On Hold");
    expect(filterStatusLabel("OPEN")).toBe("Open");
    expect(filterStatusLabel("IN_PROGRESS")).toBe("In Progress");
  });

  it("humanizes a status unique to a single module", () => {
    expect(filterStatusLabel("DUE_SOON")).toBe("Due Soon");
    expect(filterStatusLabel("RESOLVED")).toBe("Resolved");
    expect(filterStatusLabel("COMPLETED")).toBe("Completed");
  });

  it("falls back to the raw value for an unknown status", () => {
    expect(filterStatusLabel("UNKNOWN")).toBe("UNKNOWN");
  });
});

describe("buildAssetTimeline", () => {
  it("merges PM, CM, and Work Order events for a single asset", () => {
    const timeline = buildAssetTimeline("641-P-5");

    expect(timeline).toHaveLength(3);
    expect(timeline.map((event) => event.id).sort()).toEqual(["CM-3001", "PM-2008", "WO-1001"]);
  });

  it("sorts events in descending chronological order", () => {
    const timeline = buildAssetTimeline("641-P-5");

    const pmEvent = timeline.find((event) => event.id === "PM-2008");
    expect(timeline.indexOf(pmEvent)).toBe(timeline.length - 1);
  });

  it("returns an empty array for an asset with no history", () => {
    expect(buildAssetTimeline("NO-SUCH-TAG")).toEqual([]);
  });

  it("attaches the raw source record to every event", () => {
    const timeline = buildAssetTimeline("641-P-5");
    const cmEvent = timeline.find((event) => event.id === "CM-3001");

    expect(cmEvent.raw.failureDescription).toContain("seal failure");
    expect(cmEvent.title).toBe(cmEvent.raw.failureDescription);
  });
});

describe("buildAssetSummary", () => {
  it("derives every summary field from the pump and its timeline", () => {
    const pump = findAssetByTag("641-P-5");
    const timeline = buildAssetTimeline("641-P-5");

    const summary = buildAssetSummary(pump, timeline);

    expect(summary.pump).toBe(pump.name);
    expect(summary.tag).toBe("641-P-5");
    expect(summary.area).toBe(pump.area);
    expect(summary.status).toBe(pump.status);
    expect(summary.criticality).toBe(pump.criticality);
    expect(summary.lastPreventiveMaintenance).toBe("2025-12-10");
    expect(summary.lastCorrectiveMaintenance).toBe("2026-07-18");
    expect(summary.openWorkOrders).toBe(1);
    expect(summary.lastActivity).toBe(timeline[0].date);
  });

  it("reports zero open work orders and null history dates when there is none", () => {
    const pump = findAssetByTag("211-P-1B");
    const timeline = buildAssetTimeline("NO-SUCH-TAG");

    const summary = buildAssetSummary(pump, timeline);

    expect(summary.openWorkOrders).toBe(0);
    expect(summary.lastPreventiveMaintenance).toBeNull();
    expect(summary.lastCorrectiveMaintenance).toBeNull();
    expect(summary.lastActivity).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import {
  buildActivityTrend,
  buildCriticalityDistribution,
  buildRecommendedActions,
} from "./analytics";

const source = {
  pumps: [
    { tag: "211-P-1A", name: "FRESH FEED CHARGE PUMP", criticality: "HIGH", status: "RUNNING" },
    { tag: "220-P-4A", name: "Pump 4A", criticality: "LOW", status: "RUNNING" },
  ],
  workOrders: [{ id: "WO-1", equipmentTag: "211-P-1A", status: "OPEN", createdDate: "2026-07-19" }],
  pmSchedules: [{ id: "PM-1", status: "OVERDUE" }],
  cmReports: [{ cm_report_code: "CM-1", asset_code: "211-P-1A", status: "OPEN", severity: "LOW", created_at: "2026-07-19T00:00:00Z" }],
  pmOccurrences: [{ pm_occurrence_code: "PMO-1", occurrence_date: "2026-07-18" }],
  maintenanceHistory: [],
  conditionMonitoringReadings: [],
};

describe("buildActivityTrend", () => {
  it("returns four weekly buckets, oldest first, ending in This Week", () => {
    const trend = buildActivityTrend(source);

    expect(trend.buckets.map((bucket) => bucket.label)).toEqual([
      "4 Weeks Ago",
      "3 Weeks Ago",
      "2 Weeks Ago",
      "This Week",
    ]);
  });

  it("counts only supplied production events and no sample fallback", () => {
    const trend = buildActivityTrend(source);
    const bucketedTotal = trend.buckets.reduce((sum, bucket) => sum + bucket.total, 0);

    expect(bucketedTotal).toBe(3);
    expect(trend.buckets.reduce((sum, bucket) => sum + bucket.pmCount, 0)).toBe(1);
    expect(trend.buckets.reduce((sum, bucket) => sum + bucket.cmCount, 0)).toBe(1);
    expect(trend.buckets.reduce((sum, bucket) => sum + bucket.woCount, 0)).toBe(1);
  });

  it("returns empty trend buckets when no production events exist", () => {
    const trend = buildActivityTrend();

    expect(trend.buckets.every((bucket) => bucket.total === 0)).toBe(true);
    expect(trend.correctiveMaintenanceDirection).toBe("FLAT");
  });
});

describe("buildCriticalityDistribution", () => {
  it("counts supplied production pumps only", () => {
    expect(buildCriticalityDistribution(source)).toEqual([
      { criticality: "HIGH", count: 1 },
      { criticality: "LOW", count: 1 },
    ]);
  });

  it("returns no distribution when no production pumps exist", () => {
    expect(buildCriticalityDistribution()).toEqual([]);
  });
});

describe("buildRecommendedActions", () => {
  it("recommends actions only from supplied production metrics", () => {
    const actions = buildRecommendedActions(source);

    expect(actions.map((action) => action.id)).toContain("overdue-pm");
    expect(actions.map((action) => action.id)).toContain("open-cm");
    expect(actions.map((action) => action.id)).toContain("attention-assets");
  });

  it("returns no sample recommendations when no production data exists", () => {
    expect(buildRecommendedActions()).toEqual([]);
  });
});

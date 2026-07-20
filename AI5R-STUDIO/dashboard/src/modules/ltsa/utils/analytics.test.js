import { describe, expect, it } from "vitest";
import {
  buildActivityTrend,
  buildCriticalityDistribution,
  buildRecommendedActions,
} from "./analytics";
import { buildAttentionAssets, buildKpiSummary, buildMaintenanceHealth, daysBeforeReference } from "./executiveDashboard";
import { buildPlantTimeline } from "./maintenanceHistory";
import samplePumps from "../data/samplePumps";

describe("buildActivityTrend", () => {
  it("returns four weekly buckets, oldest first, ending in This Week", () => {
    const trend = buildActivityTrend();

    expect(trend.buckets.map((bucket) => bucket.label)).toEqual([
      "4 Weeks Ago",
      "3 Weeks Ago",
      "2 Weeks Ago",
      "This Week",
    ]);
  });

  it("accounts for every plant event within the last 28 days, and no others", () => {
    const trend = buildActivityTrend();
    const bucketedTotal = trend.buckets.reduce((sum, bucket) => sum + bucket.total, 0);

    const expectedTotal = buildPlantTimeline().filter((event) => {
      const days = daysBeforeReference(event.date);
      return days !== null && days >= 0 && days < 28;
    }).length;

    expect(bucketedTotal).toBe(expectedTotal);
  });

  it("splits each bucket's total across PM/CM/WO counts consistently", () => {
    const trend = buildActivityTrend();

    trend.buckets.forEach((bucket) => {
      expect(bucket.pmCount + bucket.cmCount + bucket.woCount).toBe(bucket.total);
    });
  });

  it("reports a valid corrective maintenance trend direction", () => {
    const trend = buildActivityTrend();

    expect(["UP", "DOWN", "FLAT"]).toContain(trend.correctiveMaintenanceDirection);

    const [previousWeek, lastWeek] = trend.buckets.slice(-2);
    if (lastWeek.cmCount > previousWeek.cmCount) {
      expect(trend.correctiveMaintenanceDirection).toBe("UP");
    } else if (lastWeek.cmCount < previousWeek.cmCount) {
      expect(trend.correctiveMaintenanceDirection).toBe("DOWN");
    } else {
      expect(trend.correctiveMaintenanceDirection).toBe("FLAT");
    }
  });
});

describe("buildCriticalityDistribution", () => {
  it("counts every pump exactly once, across only the criticality levels present", () => {
    const distribution = buildCriticalityDistribution();

    const total = distribution.reduce((sum, entry) => sum + entry.count, 0);
    expect(total).toBe(samplePumps.length);

    distribution.forEach((entry) => {
      expect(["HIGH", "MEDIUM", "LOW"]).toContain(entry.criticality);
      expect(entry.count).toBeGreaterThan(0);
    });
  });

  it("orders entries HIGH, then MEDIUM, then LOW", () => {
    const distribution = buildCriticalityDistribution();
    const order = distribution.map((entry) => entry.criticality);
    const expectedOrder = ["HIGH", "MEDIUM", "LOW"].filter((level) => order.includes(level));

    expect(order).toEqual(expectedOrder);
  });
});

describe("buildRecommendedActions", () => {
  it("recommends scheduling overdue PM when there is any", () => {
    const kpis = buildKpiSummary();
    const actions = buildRecommendedActions();
    const overdueAction = actions.find((action) => action.id === "overdue-pm");

    if (kpis.overduePM > 0) {
      expect(overdueAction).toBeTruthy();
      expect(overdueAction.text).toContain(String(kpis.overduePM));
    } else {
      expect(overdueAction).toBeUndefined();
    }
  });

  it("recommends reviewing attention assets when there are any", () => {
    const attentionAssets = buildAttentionAssets();
    const actions = buildRecommendedActions();
    const attentionAction = actions.find((action) => action.id === "attention-assets");

    if (attentionAssets.length > 0) {
      expect(attentionAction).toBeTruthy();
      expect(attentionAction.text).toContain(String(attentionAssets.length));
    } else {
      expect(attentionAction).toBeUndefined();
    }
  });

  it("recommends clearing the work order backlog when open exceeds closed", () => {
    const health = buildMaintenanceHealth();
    const actions = buildRecommendedActions();
    const backlogAction = actions.find((action) => action.id === "wo-backlog");

    if (health.openWorkOrders > health.closedWorkOrders) {
      expect(backlogAction).toBeTruthy();
    } else {
      expect(backlogAction).toBeUndefined();
    }
  });

  it("every action has an id, a severity, and non-empty text", () => {
    const actions = buildRecommendedActions();

    expect(actions.length).toBeGreaterThan(0);
    actions.forEach((action) => {
      expect(action.id).toBeTruthy();
      expect(["danger", "warning", "info"]).toContain(action.severity);
      expect(action.text.length).toBeGreaterThan(0);
    });
  });
});

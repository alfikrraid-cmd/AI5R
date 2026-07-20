import { describe, expect, it } from "vitest";
import {
  buildAttentionAssets,
  buildKpiSummary,
  buildMaintenanceHealth,
  buildRecentActivities,
  buildUpcomingMaintenance,
} from "./executiveDashboard";
import samplePMSchedules from "../data/samplePMSchedules";
import sampleCMReports from "../data/sampleCMReports";
import sampleWorkOrders from "../data/sampleWorkOrders";

describe("buildKpiSummary", () => {
  it("derives every KPI from the current sample data, matching a manual recount", () => {
    const kpis = buildKpiSummary();

    const expectedOpenWO = sampleWorkOrders.filter((wo) =>
      ["OPEN", "IN_PROGRESS", "ON_HOLD"].includes(wo.status)
    ).length;
    const expectedOverduePM = samplePMSchedules.filter((pm) => pm.status === "OVERDUE").length;
    const expectedUpcomingPM = samplePMSchedules.filter((pm) => pm.status === "DUE_SOON").length;
    const expectedOpenCM = sampleCMReports.filter((cm) =>
      ["OPEN", "IN_PROGRESS"].includes(cm.status)
    ).length;

    expect(kpis.openWorkOrders).toBe(expectedOpenWO);
    expect(kpis.overduePM).toBe(expectedOverduePM);
    expect(kpis.upcomingPM).toBe(expectedUpcomingPM);
    expect(kpis.openCorrectiveMaintenance).toBe(expectedOpenCM);
    expect(kpis.criticalAssets).toBeGreaterThan(0);
    expect(kpis.recentMaintenanceActivity).toBeGreaterThan(0);
  });

  it("counts critical assets consistently with buildAttentionAssets", () => {
    const kpis = buildKpiSummary();
    const attentionAssets = buildAttentionAssets();

    expect(kpis.criticalAssets).toBe(attentionAssets.length);
  });
});

describe("buildMaintenanceHealth", () => {
  it("computes a PM compliance percentage as (total - overdue) / total", () => {
    const health = buildMaintenanceHealth();

    const overdue = samplePMSchedules.filter((pm) => pm.status === "OVERDUE").length;
    const expectedRate = Math.round(((samplePMSchedules.length - overdue) / samplePMSchedules.length) * 100);

    expect(health.totalPM).toBe(samplePMSchedules.length);
    expect(health.overduePM).toBe(overdue);
    expect(health.pmComplianceRate).toBe(expectedRate);
  });

  it("splits work orders into open and closed", () => {
    const health = buildMaintenanceHealth();

    expect(health.totalWorkOrders).toBe(sampleWorkOrders.length);
    expect(health.closedWorkOrders).toBe(
      sampleWorkOrders.filter((wo) => wo.status === "COMPLETED").length
    );
    expect(health.openWorkOrders).toBe(health.totalWorkOrders - health.closedWorkOrders);
  });

  it("counts corrective maintenance reports by status", () => {
    const health = buildMaintenanceHealth();

    const total = Object.values(health.cmStatusCounts).reduce((sum, count) => sum + count, 0);
    expect(total).toBe(sampleCMReports.length);
  });
});

describe("buildAttentionAssets", () => {
  it("returns only high-criticality pumps in a concerning state or with an open work order", () => {
    const assets = buildAttentionAssets();

    expect(assets.length).toBeGreaterThan(0);
    assets.forEach((asset) => {
      expect(asset.criticality).toBe("HIGH");
      expect(asset.status === "FAULT" || asset.status === "MAINTENANCE" || asset.openWorkOrders > 0).toBe(
        true
      );
    });
  });

  it("sorts assets with the most open work orders first", () => {
    const assets = buildAttentionAssets();

    for (let i = 1; i < assets.length; i += 1) {
      expect(assets[i - 1].openWorkOrders).toBeGreaterThanOrEqual(assets[i].openWorkOrders);
    }
  });
});

describe("buildUpcomingMaintenance", () => {
  it("returns only PM schedules that are due soon or overdue", () => {
    const upcoming = buildUpcomingMaintenance();

    expect(upcoming.length).toBeGreaterThan(0);
    upcoming.forEach((pm) => {
      expect(["DUE_SOON", "OVERDUE"]).toContain(pm.status);
    });
  });

  it("sorts by next due date, soonest first", () => {
    const upcoming = buildUpcomingMaintenance();

    for (let i = 1; i < upcoming.length; i += 1) {
      expect(upcoming[i - 1].nextDue <= upcoming[i].nextDue).toBe(true);
    }
  });
});

describe("buildRecentActivities", () => {
  it("returns the most recent events across the whole plant, newest first", () => {
    const activities = buildRecentActivities(5);

    expect(activities).toHaveLength(5);
    for (let i = 1; i < activities.length; i += 1) {
      expect(activities[i - 1].date >= activities[i].date).toBe(true);
    }
  });

  it("defaults to a limit of 8", () => {
    expect(buildRecentActivities()).toHaveLength(8);
  });
});

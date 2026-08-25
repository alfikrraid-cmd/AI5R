import { describe, expect, it } from "vitest";
import {
  buildAttentionAssets,
  buildEngineeringAlerts,
  buildEngineeringReadiness,
  buildKpiSummary,
  buildMaintenanceHealth,
  buildRecentActivities,
  buildUpcomingMaintenance,
} from "./executiveDashboard";

const source = {
  pumps: [
    { tag: "211-P-1A", name: "FRESH FEED CHARGE PUMP", area: "REAKTOR", status: "RUNNING", criticality: "HIGH" },
    { tag: "220-P-4A", name: "Pump 4A", area: "UTILITIES", status: "FAULT", criticality: "HIGH" },
  ],
  workOrders: [
    { id: "WO-REAL-1", equipmentTag: "220-P-4A", status: "OPEN", priority: "CRITICAL", createdDate: "2026-07-18" },
    { id: "WO-REAL-2", equipmentTag: "211-P-1A", status: "COMPLETED", priority: "LOW", createdDate: "2026-07-10" },
  ],
  pmSchedules: [
    { id: "PM-REAL-1", status: "OVERDUE", nextDue: "2026-07-21" },
    { id: "PM-REAL-2", status: "DUE_SOON", nextDue: "2026-07-25" },
  ],
  cmReports: [
    { cm_report_code: "CM-REAL-1", asset_code: "220-P-4A", status: "OPEN", severity: "CRITICAL", created_at: "2026-07-19T00:00:00Z" },
  ],
  maintenanceHistory: [{ maintenance_record_code: "MH-REAL-1", performed_at: "2026-07-19T00:00:00Z", action_taken: "Checked" }],
  pmOccurrences: [{ pm_occurrence_code: "PMO-REAL-1", occurrence_date: "2026-07-18" }],
  conditionMonitoringReadings: [{ condition_monitoring_reading_code: "CMON-REAL-1", reading_date: "2026-07-17" }],
};

describe("buildKpiSummary", () => {
  it("derives KPIs from supplied production API data only", () => {
    expect(buildKpiSummary(source)).toMatchObject({
      openWorkOrders: 1,
      overduePM: 1,
      upcomingPM: 1,
      openCorrectiveMaintenance: 1,
      criticalAssets: 1,
      totalPumps: 2,
      criticalFailures: 1,
    });
  });

  it("returns empty/N/A-safe defaults when no production records exist", () => {
    expect(buildKpiSummary()).toMatchObject({
      openWorkOrders: 0,
      overduePM: 0,
      upcomingPM: 0,
      openCorrectiveMaintenance: 0,
      criticalAssets: 0,
      totalPumps: 0,
    });
  });
});

describe("buildEngineeringReadiness", () => {
  it("computes pump readiness from supplied production pumps", () => {
    expect(buildEngineeringReadiness(source).pump).toBe(50);
  });

  it("does not fabricate readiness when pump data is absent", () => {
    expect(buildEngineeringReadiness().pump).toBeNull();
  });
});

describe("buildEngineeringAlerts", () => {
  it("counts alerts from supplied production API records", () => {
    expect(buildEngineeringAlerts(source)).toEqual({
      overduePM: 1,
      criticalOpenCM: 1,
      criticalOpenWorkOrders: 1,
    });
  });
});

describe("buildMaintenanceHealth", () => {
  it("computes health from supplied production API records", () => {
    expect(buildMaintenanceHealth(source)).toEqual({
      pmComplianceRate: 50,
      totalPM: 2,
      overduePM: 1,
      totalWorkOrders: 2,
      openWorkOrders: 1,
      closedWorkOrders: 1,
      cmStatusCounts: { OPEN: 1 },
    });
  });

  it("does not fabricate PM compliance when PM schedules are absent", () => {
    expect(buildMaintenanceHealth().pmComplianceRate).toBeNull();
  });
});

describe("buildAttentionAssets", () => {
  it("uses production pump identities without overriding 211-P-1A with sample metadata", () => {
    const assets = buildAttentionAssets(source);

    expect(assets).toHaveLength(1);
    expect(assets[0].tag).toBe("220-P-4A");
    expect(assets.map((asset) => asset.pump).join(" ")).not.toContain("Boiler Feedwater");
  });
});

describe("buildUpcomingMaintenance", () => {
  it("returns due soon and overdue PM schedules from supplied data", () => {
    expect(buildUpcomingMaintenance(source)).toHaveLength(2);
  });
});

describe("buildRecentActivities", () => {
  it("returns the most recent supplied production events", () => {
    const activities = buildRecentActivities(source, 3);

    expect(activities.map((activity) => activity.id)).toEqual(["CM-REAL-1", "MH-REAL-1", "WO-REAL-1"]);
  });

  it("returns no sample activities when no production data is supplied", () => {
    expect(buildRecentActivities()).toEqual([]);
  });
});

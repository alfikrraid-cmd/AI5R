import { describe, expect, it } from "vitest";
import {
  ASSET_STATUS_BARS,
  CANONICAL_PUMP_STATUSES,
  computeAssetStatusByArea,
  computeCMTrend,
  computeDashboardKpis,
  computeMaintenanceActivityTrend,
  computeMechanicalSealInventory,
  computePMCompliance,
  computeSealCondition,
  computeSealUsageTrend,
  computeTopRiskPumps,
  normalizePumpStatus,
} from "./engineeringDashboardData";

describe("engineeringDashboardData -- Data Semantics & Normalization", () => {
  it("normalizes diverse pump statuses into canonical statuses", () => {
    expect(normalizePumpStatus("RUNNING")).toBe("OPERATIONAL");
    expect(normalizePumpStatus("active")).toBe("OPERATIONAL");
    expect(normalizePumpStatus("OPERATIONAL")).toBe("OPERATIONAL");
    expect(normalizePumpStatus("IDLE")).toBe("STANDBY");
    expect(normalizePumpStatus("standby")).toBe("STANDBY");
    expect(normalizePumpStatus("MAINTENANCE")).toBe("MAINTENANCE");
    expect(normalizePumpStatus("under_maintenance")).toBe("MAINTENANCE");
    expect(normalizePumpStatus("FAULT")).toBe("FAULT");
    expect(normalizePumpStatus("failed")).toBe("FAULT");
    expect(normalizePumpStatus("UNKNOWN")).toBe("UNKNOWN");
    expect(normalizePumpStatus(null)).toBe("UNKNOWN");
    expect(normalizePumpStatus(undefined)).toBe("UNKNOWN");
  });

  it("defines exactly the 5 canonical statuses and bar configurations", () => {
    expect(CANONICAL_PUMP_STATUSES).toEqual([
      "OPERATIONAL",
      "STANDBY",
      "MAINTENANCE",
      "FAULT",
      "UNKNOWN",
    ]);
    expect(ASSET_STATUS_BARS.map((b) => b.key)).toEqual(CANONICAL_PUMP_STATUSES);
  });
});

describe("engineeringDashboardData -- Row 2: Asset Status by Area (Stacked Bar)", () => {
  const samplePumps = [
    { tag_number: "P-101", area: "Reaktor", status: "RUNNING" },
    { tag_number: "P-102", area: "Reaktor", status: "STANDBY" },
    { tag_number: "P-103", area: "Reaktor", status: "FAULT" },
    { tag_number: "P-201", area: "Utility", status: "OPERATIONAL" },
    { tag_number: "P-202", area: "Utility", status: "MAINTENANCE" },
    { tag_number: "P-301", area: "Offsite", status: "UNKNOWN" },
  ];

  it("groups pumps by area and counts canonical statuses", () => {
    const result = computeAssetStatusByArea(samplePumps);
    expect(result).toHaveLength(3);

    const reaktor = result.find((r) => r.area === "Reaktor");
    expect(reaktor.OPERATIONAL).toBe(1);
    expect(reaktor.STANDBY).toBe(1);
    expect(reaktor.FAULT).toBe(1);
    expect(reaktor.MAINTENANCE).toBe(0);
    expect(reaktor.total).toBe(3);

    const utility = result.find((r) => r.area === "Utility");
    expect(utility.OPERATIONAL).toBe(1);
    expect(utility.MAINTENANCE).toBe(1);
    expect(utility.total).toBe(2);
  });

  it("filters by area when areaFilter is provided", () => {
    const result = computeAssetStatusByArea(samplePumps, "Reaktor");
    expect(result).toHaveLength(1);
    expect(result[0].area).toBe("Reaktor");
    expect(result[0].total).toBe(3);
  });

  it("handles empty array gracefully", () => {
    expect(computeAssetStatusByArea([])).toEqual([]);
    expect(computeAssetStatusByArea(null)).toEqual([]);
  });
});

describe("engineeringDashboardData -- Row 2: PM Compliance (Donut)", () => {
  const sampleSchedules = [
    { asset_code: "P-101", status: "COMPLETED" },
    { asset_code: "P-102", status: "DONE" },
    { asset_code: "P-103", status: "ACTIVE" },
    { asset_code: "P-201", status: "OVERDUE" },
    { asset_code: "P-202", status: "PLANNED" },
  ];

  it("calculates donut slices for canonical PM schedule statuses", () => {
    const slices = computePMCompliance(sampleSchedules);
    expect(slices).toEqual([
      expect.objectContaining({ label: "Completed", value: 2 }),
      expect.objectContaining({ label: "Due", value: 1 }),
      expect.objectContaining({ label: "Overdue", value: 1 }),
      expect.objectContaining({ label: "Planned", value: 1 }),
    ]);
  });

  it("filters by area using pumpAreaMap", () => {
    const pumpAreaMap = {
      "P-101": "Reaktor",
      "P-102": "Reaktor",
      "P-103": "Reaktor",
      "P-201": "Utility",
      "P-202": "Utility",
    };
    const slices = computePMCompliance(sampleSchedules, "Reaktor", pumpAreaMap);
    expect(slices).toEqual([
      expect.objectContaining({ label: "Completed", value: 2 }),
      expect.objectContaining({ label: "Due", value: 1 }),
    ]);
  });
});

describe("engineeringDashboardData -- Row 3: Condition Monitoring Trend (Line)", () => {
  const sampleReadings = [
    {
      asset_code: "P-101",
      reading_date: "2026-05-10",
      overall_condition: "NORMAL",
      mechanical_seal_leak_de: false,
      mechanical_seal_leak_nde: false,
    },
    {
      asset_code: "P-102",
      reading_date: "2026-05-15",
      overall_condition: "ATTENTION",
      mechanical_seal_leak_de: true,
      mechanical_seal_leak_nde: false,
    },
    {
      asset_code: "P-103",
      reading_date: "2026-06-02",
      overall_condition: "CRITICAL",
      mechanical_seal_leak_de: false,
      mechanical_seal_leak_nde: true,
    },
  ];

  it("aggregates readings by month and counts abnormal findings and leaks", () => {
    const trend = computeCMTrend(sampleReadings);
    expect(trend).toHaveLength(2);
    expect(trend[0]).toEqual({
      date: "2026-05",
      total_readings: 2,
      abnormal_count: 1,
      leak_count: 1,
    });
    expect(trend[1]).toEqual({
      date: "2026-06",
      total_readings: 1,
      abnormal_count: 1,
      leak_count: 1,
    });
  });
});

describe("engineeringDashboardData -- Row 3: Mechanical Seal Condition (Donut)", () => {
  it("strictly classifies seal condition according to canonical rules", () => {
    const readings = [
      {
        asset_code: "P-1",
        reading_date: "2026-05-01",
        overall_condition: "NORMAL",
        mechanical_seal_leak_de: false,
        mechanical_seal_leak_nde: false,
      },
      {
        asset_code: "P-2",
        reading_date: "2026-05-01",
        overall_condition: "ATTENTION",
        mechanical_seal_leak_de: false,
        mechanical_seal_leak_nde: false,
      },
      {
        asset_code: "P-3",
        reading_date: "2026-05-01",
        overall_condition: "ATTENTION",
        mechanical_seal_leak_de: true,
        mechanical_seal_leak_nde: false,
      },
    ];

    const workOrders = [
      { asset_code: "P-4", work_type: "SEAL_REPLACEMENT", status: "OPEN" },
    ];

    const recommendations = [
      { tag_number: "P-5", priority: 100, rule_code: "REC_CRITICAL_CM" },
    ];

    const slices = computeSealCondition(readings, workOrders, recommendations);
    expect(slices).toEqual([
      expect.objectContaining({ label: "Normal", value: 1 }),
      expect.objectContaining({ label: "Under Observation", value: 1 }),
      expect.objectContaining({ label: "Leak Evidence", value: 1 }),
      expect.objectContaining({ label: "Replacement Required", value: 2 }),
    ]);
  });
});

describe("engineeringDashboardData -- Row 4: Maintenance Activity Trend (Grouped Bar)", () => {
  it("aggregates PMs, CMs, and Seal Replacements into monthly buckets", () => {
    const result = computeMaintenanceActivityTrend({
      pmOccurrences: [{ occurrence_date: "2026-05-01" }, { occurrence_date: "2026-05-15" }],
      cmReports: [{ created_at: "2026-05-12" }],
      installations: [{ installation_date: "2026-05-20" }],
    });

    expect(result).toEqual([
      {
        month: "2026-05",
        pm_count: 2,
        cm_count: 1,
        seal_replacements: 1,
      },
    ]);
  });
});

describe("engineeringDashboardData -- Row 5: Top Risk Pumps & Mechanical Seal Inventory", () => {
  it("ranks top risk pumps descending by risk score", () => {
    const badActors = [
      { pump_tag: "P-101", leak_count: 3, cmon_readings: 10, area: "Reaktor" },
      { pump_tag: "P-102", leak_count: 1, cmon_readings: 5, area: "Utility" },
    ];
    const result = computeTopRiskPumps([], badActors);
    expect(result).toHaveLength(2);
    expect(result[0].pump_tag).toBe("P-101");
    expect(result[0].risk_score).toBeGreaterThan(result[1].risk_score);
  });

  it("visualizes actual canonical seal quantities without invented low-stock thresholds", () => {
    const stocks = [
      {
        seal_code: "SEAL-A",
        quantity_on_hand: 10,
        quantity_available: 8,
        quantity_reserved: 2,
      },
      {
        seal_code: "SEAL-B",
        quantity_on_hand: 4,
        quantity_available: 4,
        quantity_reserved: 0,
      },
    ];

    const result = computeMechanicalSealInventory(stocks);
    expect(result).toEqual([
      {
        seal_code: "SEAL-A",
        quantity_on_hand: 10,
        quantity_available: 8,
        quantity_reserved: 2,
      },
      {
        seal_code: "SEAL-B",
        quantity_on_hand: 4,
        quantity_available: 4,
        quantity_reserved: 0,
      },
    ]);
  });
});

describe("engineeringDashboardData -- Row 1: KPI Strip Calculations", () => {
  it("calculates Row 1 KPIs correctly and returns N/A for absent reliability score", () => {
    const kpis = computeDashboardKpis({
      overview: { pump_count: 12, pm_schedule_count: 5 },
      reliability: null,
      summary: null,
      readings: [{ mechanical_seal_leak_de: true }],
    });

    expect(kpis.fleetHealth).toBeNull(); // N/A, never invented
    expect(kpis.totalPumps).toBe(12);
    expect(kpis.activeLeaks).toBe(1);
    expect(kpis.pmDue).toBe(5);
  });

  it("uses canonical reliability score when provided", () => {
    const kpis = computeDashboardKpis({
      reliability: { fleet_health_score: 87.5, total_critical_spare_count: 3 },
    });
    expect(kpis.fleetHealth).toBe(87.5);
    expect(kpis.criticalSpare).toBe(3);
  });
});

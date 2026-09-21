import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ExecutiveDashboard from "./ExecutiveDashboard";
import {
  getFleetOverview,
  getFleetPowerBI,
  getFleetReliability,
  getLtsaAnalyticsExecutive,
  getLtsaAnalyticsSeals,
} from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getFleetOverview: vi.fn(),
  getFleetReliability: vi.fn(),
  getFleetPowerBI: vi.fn(),
  getLtsaAnalyticsFilters: vi.fn().mockResolvedValue({
    areas: [{ area: "Reaktor", pump_count: 10 }, { area: "Utility", pump_count: 5 }],
    pumps: [{ tag_number: "641-P-5", area: "Reaktor" }],
    date_range: { min_date: "2026-07-01", max_date: "2026-07-31" },
  }),
  getLtsaAnalyticsExecutive: vi.fn(),
  getLtsaAnalyticsSeals: vi.fn(),
  getLtsaAnalyticsMaterials: vi.fn().mockResolvedValue(null),
  getLtsaAnalyticsEffectiveness: vi.fn().mockResolvedValue(null),
}));

vi.mock("../components/CopilotPanel", () => ({
  default: () => <div data-testid="mock-copilot-content">Copilot Content</div>,
}));

function mockOverview() {
  return {
    success: true,
    data: {
      pump_count: 15,
      area_distribution: { Reaktor: 10, Utility: 5 },
      contract_area_distribution: { Reaktor: 10, Utility: 5 },
      status_distribution: { RUNNING: 12, STANDBY: 3 },
      work_order_count: 4,
      work_order_status_distribution: { OPEN: 2, CLOSED: 2 },
      pm_schedule_count: 8,
      cm_report_count: 3,
      seal_stock_count: 18,
      low_stock_seal_count: 2,
    },
  };
}

function mockReliability() {
  return {
    success: true,
    data: {
      pump_count: 15,
      fleet_health_score: 92.4,
      total_critical_spare_count: 6,
      total_breakdown_count: 1,
    },
  };
}

function mockPowerBI() {
  return {
    success: true,
    data: {
      overall_health: 92.4,
      fleet_status: "NORMAL",
      critical_asset_count: 1,
      critical_spare_count: 6,
      top_risks: [
        {
          tag_number: "641-P-5",
          rule_code: "REC_CRITICAL_CM",
          priority: 100,
          area: "Reaktor",
        },
      ],
    },
  };
}

function mockExecutiveAnalytics() {
  return {
    kpis: {
      total_pumps: 15,
      active_pumps: 14,
      monitored_pumps: 15,
      pm_executed_count: 12,
      pm_done_count: 12,
      pm_scheduled_count: 15,
      pm_compliance_percent: 80.0,
      confirmed_seal_leaks: 3,
      de_leaks: 2,
      nde_leaks: 1,
      breakdown_count: 0,
      fleet_mtbf_days: null,
      fleet_mttr_hours: null,
      fleet_availability: null,
    },
    trends: {
      daily: [
        { date: "2026-07-01", pm_count: 2, cmon_readings: 4, seal_leaks: 1 },
        { date: "2026-07-02", pm_count: 3, cmon_readings: 5, seal_leaks: 0 },
        { date: "2026-07-03", pm_count: 1, cmon_readings: 3, seal_leaks: 2 },
      ],
    },
    area_breakdown: [
      { area: "Reaktor", pump_count: 10, pm_count: 8, cmon_readings: 12, seal_leaks: 2 },
      { area: "Utility", pump_count: 5, pm_count: 4, cmon_readings: 6, seal_leaks: 1 },
    ],
    top_bad_actors: [
      {
        pump_tag: "641-P-5",
        area: "Reaktor",
        pump_type: "OH2",
        api_plan: "Plan 53A",
        leak_count: 2,
        cmon_readings: 8,
        pm_count: 4,
        latest_leak_date: "2026-07-03",
      },
    ],
    historical_findings: [],
  };
}

describe("ExecutiveDashboard -- Diagram-First Engineering Analytics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getFleetOverview.mockResolvedValue(mockOverview());
    getFleetReliability.mockResolvedValue(mockReliability());
    getFleetPowerBI.mockResolvedValue(mockPowerBI());
    getLtsaAnalyticsExecutive.mockResolvedValue(mockExecutiveAnalytics());
    getLtsaAnalyticsSeals.mockResolvedValue(null);
  });

  it("renders Row 1 KPI Strip with all 6 required engineering cards", async () => {
    render(<ExecutiveDashboard />);

    await waitFor(() => expect(screen.getByTestId("kpi-fleet-health")).toBeTruthy());

    // 1. Fleet Health
    expect(screen.getByTestId("kpi-fleet-health").textContent).toMatch(/92[.,]4%/);
    // 2. Total Pumps
    expect(screen.getByTestId("kpi-total-pumps").textContent).toContain("15");
    // 3. Active Leak / Abnormal Finding
    expect(screen.getByTestId("kpi-confirmed-leaks").textContent).toContain("3");
    // 4. PM Due
    expect(screen.getByTestId("kpi-pm-executed").textContent).toContain("15");
    // 5. PM Overdue
    expect(screen.getByTestId("kpi-pm-compliance")).toBeTruthy();
    // 6. Critical Spare
    expect(screen.getByTestId("kpi-critical-spare").textContent).toContain("6");
  });

  it("renders Row 2: Asset Status by Area (Stacked Bar) and PM Compliance (Donut)", async () => {
    render(<ExecutiveDashboard />);

    // Row 2 Left: Asset Status by Area (NOT Fleet Health by Area)
    expect(await screen.findByText("Asset Status by Area")).toBeTruthy();
    expect(screen.getByText("Stacked Canonical Status")).toBeTruthy();

    // Row 2 Right: PM Compliance
    expect(screen.getByText("PM Compliance")).toBeTruthy();
    expect(screen.getByText("Schedule Adherence")).toBeTruthy();
  });

  it("renders Row 3: Condition Monitoring Trend (Line) and Mechanical Seal Condition (Donut)", async () => {
    render(<ExecutiveDashboard />);

    // Row 3 Left: Condition Monitoring Trend
    const cmElements = await screen.findAllByText("Condition Monitoring Trend");
    expect(cmElements.length).toBeGreaterThan(0);

    // Row 3 Right: Mechanical Seal Condition
    const sealElements = screen.getAllByText("Mechanical Seal Condition");
    expect(sealElements.length).toBeGreaterThan(0);
  });

  it("renders Row 4: Maintenance Activity Trend as a full-width grouped bar chart", async () => {
    render(<ExecutiveDashboard />);

    expect(await screen.findByText("Maintenance Activity Trend")).toBeTruthy();
    expect(screen.getByText("Execution Breakdown (PM vs CM vs Seals)")).toBeTruthy();
  });

  it("renders Row 5: Top Risk Pumps (Horizontal Bar) and Mechanical Seal Inventory (Bar)", async () => {
    render(<ExecutiveDashboard />);

    // Row 5 Left: Top Risk Pumps
    expect(await screen.findByText("Top Risk Pumps")).toBeTruthy();
    expect(screen.getByText("Repeat Incidents & Criticality")).toBeTruthy();

    // Row 5 Right: Mechanical Seal Inventory with canonical quantities
    expect(screen.getByText("Mechanical Seal Inventory")).toBeTruthy();
    expect(screen.getByText("Canonical Quantities")).toBeTruthy();
  });

  it("toggles the AI Engineering Copilot drawer without displacing the main analytics width", async () => {
    render(<ExecutiveDashboard />);

    await screen.findByText("Asset Status by Area");

    // Default state: collapsed
    expect(screen.queryByRole("dialog", { name: /Copilot Drawer/i })).toBeNull();

    // Click trigger to open
    const toggleBtn = screen.getByRole("button", { name: "Toggle Copilot Drawer" });
    fireEvent.click(toggleBtn);

    expect(screen.getByRole("dialog", { name: /Copilot Drawer/i })).toBeTruthy();
    expect(screen.getByTestId("mock-copilot-content")).toBeTruthy();

    // Click close button
    const closeBtn = screen.getByRole("button", { name: "Close Copilot" });
    fireEvent.click(closeBtn);

    expect(screen.queryByRole("dialog", { name: /Copilot Drawer/i })).toBeNull();
  });
});

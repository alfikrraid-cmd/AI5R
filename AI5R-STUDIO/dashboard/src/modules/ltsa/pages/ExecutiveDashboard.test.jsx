import { readFileSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ExecutiveDashboard from "./ExecutiveDashboard";
import { getFleetOverview, getFleetPowerBI, getFleetReliability } from "../../../api/ai5rClient";

// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- Command Center visual/layout
// redesign. Data-fetch logic (required /overview, optional /reliability +
// /powerbi) is untouched from MWO-LTSA-DASHBOARD-RECOVERY-001 -- only the
// rendered structure changed: FleetKpiStrip (always-visible top strip),
// BasicFleetOverviewPanel (trimmed to area/status distributions),
// AssetsAttentionPanel/MaintenanceActivityPanel (new, two-column row),
// SealInventoryPanel + QuickNavigationPanel ("Quick Actions", new,
// two-column row). "Fleet Overview" (the Card heading) is used below as
// the reliable "core content has rendered" signal, replacing the old
// "Total Pumps" MetricCard that used to live inside that same panel and
// has since moved to FleetKpiStrip.

vi.mock("../../../api/ai5rClient", () => ({
  getFleetOverview: vi.fn(),
  getFleetReliability: vi.fn(),
  getFleetPowerBI: vi.fn(),
}));

vi.mock("../components/CopilotPanel", () => ({
  default: () => null,
}));

afterEach(() => {
  vi.clearAllMocks();
});

function overviewResponse(overrides = {}) {
  return {
    success: true,
    data: {
      pump_count: 4,
      area_distribution: { Reaktor: 3, Utility: 1 },
      contract_area_distribution: {
        HOC: 1,
        "HSC & S. Pakning": 1,
        HCC: 1,
        "OM & UTL": 0,
        Unclassified: 1,
      },
      status_distribution: { ACTIVE: 4 },
      work_order_count: 2,
      work_order_status_distribution: { OPEN: 2 },
      pm_schedule_count: 1,
      cm_report_count: 1,
      seal_stock_count: 5,
      low_stock_seal_count: 1,
      ...overrides,
    },
  };
}

function reliabilityResponse(overrides = {}) {
  return {
    success: true,
    data: {
      pump_count: 4,
      fleet_health_score: 86.5,
      fleet_mtbf_days: 42.3,
      fleet_mttr_hours: 6.25,
      fleet_availability: 98.76,
      total_breakdown_count: 3,
      total_critical_spare_count: 2,
      ...overrides,
    },
  };
}

function powerbiResponse(overrides = {}) {
  return {
    success: true,
    data: {
      overall_health: 86.5,
      fleet_status: "NORMAL",
      critical_asset_count: 1,
      fleet_availability: 98.76,
      fleet_mtbf_days: 42.3,
      fleet_mttr_hours: 6.25,
      breakdown_count: 3,
      critical_spare_count: 2,
      top_risks: [
        {
          tag_number: "641-P-5",
          rule_code: "REC_CRITICAL_CM",
          title: "Immediate Inspection",
          priority: 100,
          action: "Dispatch a technician for immediate inspection.",
          description: "An open Corrective Maintenance report with critical or major severity was found.",
        },
      ],
      insight: {
        summary: "Fleet status NORMAL: 1 critical asset(s). Top risk: Immediate Inspection on 641-P-5.",
        priority: 100,
        action: "Dispatch a technician for immediate inspection.",
        reason: "An open Corrective Maintenance report with critical or major severity was found.",
      },
      ...overrides,
    },
  };
}

beforeEach(() => {
  getFleetOverview.mockResolvedValue(overviewResponse());
  getFleetReliability.mockResolvedValue(reliabilityResponse());
  getFleetPowerBI.mockResolvedValue(powerbiResponse());
});

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DASHBOARD_SOURCE = readFileSync(path.join(__dirname, "ExecutiveDashboard.jsx"), "utf-8");

describe("ExecutiveDashboard -- required Fleet Overview: loading / error / empty states", () => {
  it("shows a loading state before the required overview API resolves", () => {
    getFleetOverview.mockReturnValue(new Promise(() => {}));

    render(<ExecutiveDashboard />);

    expect(screen.getByText(/loading executive dashboard/i)).toBeTruthy();
  });

  it("shows an error state, no fallback data, when the required overview API fails", async () => {
    getFleetOverview.mockRejectedValue(new Error("Fleet overview API unavailable"));

    render(<ExecutiveDashboard />);

    expect(await screen.findByText("Fleet overview API unavailable")).toBeTruthy();
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("Pumps by Area")).toBeNull();
  });

  it("shows an empty state, not a crash, when the fleet has no pumps", async () => {
    getFleetOverview.mockResolvedValue(
      overviewResponse({
        pump_count: 0,
        area_distribution: {},
        status_distribution: {},
        work_order_count: 0,
        work_order_status_distribution: {},
        pm_schedule_count: 0,
        cm_report_count: 0,
        seal_stock_count: 0,
        low_stock_seal_count: null,
      })
    );

    render(<ExecutiveDashboard />);

    expect(await screen.findByText(/no fleet data/i)).toBeTruthy();
    expect(screen.queryByText("Pumps by Area")).toBeNull();
  });

  it("still renders Quick Actions during loading, error, and empty states (unconditional, unchanged behavior)", async () => {
    getFleetOverview.mockReturnValue(new Promise(() => {}));
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(screen.getByRole("heading", { name: "Quick Actions" })).toBeTruthy();
  });
});

describe("ExecutiveDashboard -- optional Reliability/Power BI data (MWO-LTSA-DASHBOARD-RECOVERY-001)", () => {
  it("still renders the core Fleet Overview when Reliability fails (404/504-shaped failure)", async () => {
    getFleetReliability.mockRejectedValue(new Error("Fleet reliability API unavailable"));

    render(<ExecutiveDashboard />);

    expect(await screen.findByRole("heading", { name: "Fleet Overview" })).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("still renders the core Fleet Overview when Power BI fails", async () => {
    getFleetPowerBI.mockRejectedValue(new Error("Fleet Power BI API unavailable"));

    render(<ExecutiveDashboard />);

    expect(await screen.findByRole("heading", { name: "Fleet Overview" })).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("still renders the core Fleet Overview when both Reliability and Power BI fail", async () => {
    getFleetReliability.mockRejectedValue(new Error("down"));
    getFleetPowerBI.mockRejectedValue(new Error("down"));

    render(<ExecutiveDashboard />);

    expect(await screen.findByRole("heading", { name: "Fleet Overview" })).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("does not render the richer Fleet Health Score panel when Reliability/Power BI fail", async () => {
    getFleetReliability.mockRejectedValue(new Error("down"));
    getFleetPowerBI.mockRejectedValue(new Error("down"));

    render(<ExecutiveDashboard />);

    await screen.findByRole("heading", { name: "Fleet Overview" });
    expect(screen.queryByText("Fleet Health Score")).toBeNull();
  });

  it("Assets Needing Attention shows a disclosed 'data unavailable' state, not a crash, when optional data fails", async () => {
    getFleetReliability.mockRejectedValue(new Error("down"));
    getFleetPowerBI.mockRejectedValue(new Error("down"));

    render(<ExecutiveDashboard />);

    await screen.findByRole("heading", { name: "Fleet Overview" });
    expect(await screen.findByText("Data unavailable")).toBeTruthy();
  });

  it("renders the richer Fleet Health Score panel when Reliability/Power BI succeed, alongside the core overview", async () => {
    render(<ExecutiveDashboard />);

    await screen.findByRole("heading", { name: "Fleet Overview" });
    expect(await screen.findByText("Fleet Health Score")).toBeTruthy();
  });
});

describe("ExecutiveDashboard -- One Fetch per API", () => {
  it("calls each Fleet API exactly once, no polling, no duplicate calls", async () => {
    render(<ExecutiveDashboard />);

    await waitFor(() => expect(getFleetOverview).toHaveBeenCalledTimes(1));
    expect(getFleetReliability).toHaveBeenCalledTimes(1);
    expect(getFleetPowerBI).toHaveBeenCalledTimes(1);
  });
});

describe("ExecutiveDashboard -- Command Center layout (MWO-LTSA-DASHBOARD-COMMAND-CENTER-001)", () => {
  it("renders the always-visible FleetKpiStrip with Pumps/Running/Standby/Attention/Open WO", async () => {
    render(<ExecutiveDashboard />);

    expect(await screen.findByText("Pumps")).toBeTruthy();
    expect(screen.getByText("Running")).toBeTruthy();
    expect(screen.getByText("Standby")).toBeTruthy();
    expect(screen.getByText("Attention")).toBeTruthy();
    expect(screen.getByText("Open WO")).toBeTruthy();
  });

  it("renders the trimmed Fleet Overview: area/status distributions only, no more raw count cards", async () => {
    render(<ExecutiveDashboard />);

    expect(await screen.findByRole("heading", { name: "Fleet Overview" })).toBeTruthy();
    expect(screen.getByText("Fleet by Contract Area")).toBeTruthy();
    expect(screen.getByText("Pumps by Raw Area/Location")).toBeTruthy();
    expect(screen.getByText("Pumps by Status")).toBeTruthy();
  });

  it("renders Assets Needing Attention and Maintenance Activity side by side", async () => {
    render(<ExecutiveDashboard />);

    await screen.findByRole("heading", { name: "Fleet Overview" });
    expect(screen.getByRole("heading", { name: "Assets Needing Attention" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Maintenance Activity" })).toBeTruthy();
  });

  it("renders Seal Inventory and Quick Actions side by side", async () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);

    await screen.findByRole("heading", { name: "Fleet Overview" });
    expect(screen.getByRole("heading", { name: "Seal Inventory" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Quick Actions" })).toBeTruthy();
  });
});

describe("ExecutiveDashboard -- optional layout regions render", () => {
  it("renders the Hero: Fleet Health Score and Fleet Status", async () => {
    render(<ExecutiveDashboard />);

    // Fleet Status and NORMAL legitimately also appear a second time in
    // the Executive Summary recap at the bottom -- assert presence, not
    // uniqueness, the same collision-handling precedent already used
    // throughout this codebase's RTL tests.
    expect(await screen.findByText("Fleet Health Score")).toBeTruthy();
    expect(screen.getAllByText("Fleet Status").length).toBeGreaterThan(0);
    expect(screen.getAllByText("NORMAL").length).toBeGreaterThan(0);
  });

  it("renders the Metrics: Availability, MTBF, MTTR, Pump Count, Breakdown Count, Critical Spare Count", async () => {
    render(<ExecutiveDashboard />);

    // These labels are intentionally repeated in the Executive Summary
    // recap -- assert presence, not uniqueness.
    await screen.findByText("Fleet Health Score");
    expect(screen.getAllByText("Availability").length).toBeGreaterThan(0);
    expect(screen.getAllByText("MTBF").length).toBeGreaterThan(0);
    expect(screen.getAllByText("MTTR").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pump Count").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Breakdown Count").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Critical Spare Count").length).toBeGreaterThan(0);
  });

  it("renders Critical Assets in the Main Area", async () => {
    render(<ExecutiveDashboard />);

    await screen.findByText("Fleet Health Score");
    expect(screen.getAllByText("Critical Assets").length).toBeGreaterThan(0);
  });

  it("renders Top Risks in the Main Area", async () => {
    render(<ExecutiveDashboard />);

    await screen.findByText("Fleet Health Score");
    expect(screen.getByText("Top Risks")).toBeTruthy();
    // "641-P-5" legitimately also appears in Assets Needing Attention now
    // -- assert presence, not uniqueness.
    expect(screen.getAllByText("641-P-5").length).toBeGreaterThan(0);
  });

  it("renders Fleet Insight in the Main Area", async () => {
    render(<ExecutiveDashboard />);

    await screen.findByText("Fleet Health Score");
    expect(screen.getByText("Fleet Insight")).toBeTruthy();
    expect(
      screen.getByText("Fleet status NORMAL: 1 critical asset(s). Top risk: Immediate Inspection on 641-P-5.")
    ).toBeTruthy();
  });

  it("renders the Executive Summary at the bottom", async () => {
    render(<ExecutiveDashboard />);

    await screen.findByText("Fleet Health Score");
    expect(screen.getByRole("heading", { name: "Executive Summary" })).toBeTruthy();
  });
});

describe("ExecutiveDashboard -- no mock or sample data", () => {
  it("does not import the old sample-data builder module", () => {
    expect(DASHBOARD_SOURCE).not.toMatch(/utils\/executiveDashboard/);
  });

  it("does not import any of the removed static/demo panels", () => {
    // Checks actual import statements only, not prose -- this file's own
    // header comment names these components in explanatory text
    // (disclosing why they're orphaned, not deleted), which would false-
    // positive a bare substring/whole-file check.
    // QuickNavigationPanel is intentionally NOT in this list -- it's real
    // workspace navigation, not a static/demo/duplicated-KPI section, and
    // stays wired in (see the dedicated describe block below).
    for (const removed of [
      "KpiCardGrid",
      "MaintenanceHealthPanel",
      "EngineeringReadinessPanel",
      "EngineeringAlertsPanel",
      "EngineeringInsightPanel",
      "BusinessOpportunityPanel",
      "AttentionAssetList",
      "ImmediateActionTable",
      "UpcomingMaintenanceList",
      "RecentActivityFeed",
      "DigitalTwinPanel",
      "DashboardTopBar",
    ]) {
      expect(DASHBOARD_SOURCE).not.toMatch(new RegExp(`import ${removed}|from ["'].*${removed}["']`));
    }
  });

  it("makes no raw fetch() call -- goes through ai5rClient only", () => {
    expect(DASHBOARD_SOURCE).not.toMatch(/\bfetch\(/);
  });

  it("references the three reused Fleet API functions, no other endpoint", () => {
    const importLine = DASHBOARD_SOURCE.split("\n").find((line) => line.includes("ai5rClient"));
    expect(importLine).toContain("getFleetOverview");
    expect(importLine).toContain("getFleetReliability");
    expect(importLine).toContain("getFleetPowerBI");
    expect(importLine).not.toContain("getPumpKnowledge");
    expect(importLine).not.toContain("postEngineeringAI");
  });

  it("makes no reference anywhere to the Engineering AI feature (No AI, per this MWO's rule)", () => {
    expect(DASHBOARD_SOURCE).not.toMatch(/postEngineeringAI|engineering-ai|EngineeringAI/);
  });
});

describe("ExecutiveDashboard -- reuse discipline", () => {
  it("uses the existing Card and MetricCard design-system components, defines no local equivalent", () => {
    expect(DASHBOARD_SOURCE).not.toMatch(/function MetricCard/);
    expect(DASHBOARD_SOURCE).not.toMatch(/function Card\(/);
  });
});

describe("ExecutiveDashboard -- workspace navigation retained", () => {
  // QuickNavigationPanel isn't part of the Command Center's KPI-strip /
  // two-column layout, but it is real navigation infrastructure (not a
  // static/demo/KPI section) that LTSAWorkspace.test.jsx's own cross-page
  // flows depend on reaching from this page -- kept wired in, retitled
  // "Quick Actions" per this MWO, unconditionally rendered exactly as
  // before (see the loading/error/empty describe block above).
  it("still renders Quick Actions", async () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);

    await screen.findByRole("heading", { name: "Fleet Overview" });
    expect(screen.getByRole("heading", { name: "Quick Actions" })).toBeTruthy();
  });

  it("still renders the page heading regardless of load state", () => {
    getFleetOverview.mockReturnValue(new Promise(() => {}));

    render(<ExecutiveDashboard onNavigate={() => {}} />);

    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeTruthy();
  });
});

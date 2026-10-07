import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ExecutiveDashboard from "./ExecutiveDashboard";
import {
  getFleetOverview,
  getFleetPowerBI,
  getFleetReliability,
  getLtsaAnalyticsEffectiveness,
  getLtsaAnalyticsExecutive,
  getLtsaAnalyticsFilters,
  getLtsaAnalyticsMaterials,
  getLtsaAnalyticsSeals,
} from "../../../api/ai5rClient";

// LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- one global Area filter:
// options come only from the backend's authorized_areas, the selection is
// persisted in ?area= (never authorization), every area-dependent request
// uses the same area, previous-area data is cleared while the next area
// loads, and a backend 403 renders the Unauthorized state.

vi.mock("../../../api/ai5rClient", () => ({
  getFleetOverview: vi.fn(),
  getFleetReliability: vi.fn(),
  getFleetPowerBI: vi.fn(),
  getLtsaAnalyticsFilters: vi.fn(),
  getLtsaAnalyticsExecutive: vi.fn(),
  getLtsaAnalyticsSeals: vi.fn(),
  getLtsaAnalyticsMaterials: vi.fn(),
  getLtsaAnalyticsEffectiveness: vi.fn(),
}));

vi.mock("../components/CopilotPanel", () => ({ default: () => null }));

const AUTHORIZED = [
  { code: "HOC", label: "HOC" },
  { code: "HSC", label: "HSC" },
  { code: "S_PAKNING", label: "S. Pakning" },
  { code: "HCC", label: "HCC" },
  { code: "OM", label: "OM" },
  { code: "UTL", label: "UTL" },
];

const COUNTS = { ALL: 230, HOC: 54, HSC: 37, S_PAKNING: 10, HCC: 82, OM: 31, UTL: 16 };

function overviewFor(area) {
  return {
    success: true,
    data: {
      pump_count: COUNTS[area],
      area_distribution: {},
      contract_area_distribution: { HOC: 0, "HSC & S. Pakning": 0, HCC: 0, "OM & UTL": 0, Unclassified: 0 },
      status_distribution: {},
      work_order_count: 0,
      work_order_status_distribution: {},
      pm_schedule_count: 0,
      cm_report_count: 0,
      seal_stock_count: null,
      low_stock_seal_count: null,
    },
  };
}

function executiveFor(area) {
  return {
    kpis: { total_pumps: COUNTS[area], pm_compliance_percent: null, pm_scheduled_count: null, breakdown_count: null },
    trends: { daily: [] },
    area_breakdown: [],
    top_bad_actors: [],
    historical_findings: [],
  };
}

const areaOf = (params = {}) => params.area ?? "ALL";

function forbidden(code = "area_not_in_scope") {
  const error = new Error(code);
  error.status = 403;
  error.code = code;
  return error;
}

beforeEach(() => {
  window.history.pushState({}, "", "/ltsa/dashboard");
  getLtsaAnalyticsFilters.mockResolvedValue({ authorized_areas: AUTHORIZED, pumps: [], date_range: {} });
  getFleetOverview.mockImplementation(async (params) => overviewFor(areaOf(params)));
  getFleetReliability.mockReturnValue(new Promise(() => {}));
  getFleetPowerBI.mockReturnValue(new Promise(() => {}));
  getLtsaAnalyticsExecutive.mockImplementation(async (params) => executiveFor(areaOf(params)));
  getLtsaAnalyticsSeals.mockResolvedValue(null);
  getLtsaAnalyticsMaterials.mockResolvedValue(null);
  getLtsaAnalyticsEffectiveness.mockResolvedValue(null);
});

afterEach(() => {
  vi.clearAllMocks();
});

async function selectArea(code) {
  await waitFor(() => expect(screen.getByLabelText("Filter by Area").querySelectorAll("option").length).toBe(7));
  fireEvent.change(screen.getByLabelText("Filter by Area"), { target: { value: code } });
}

function totalPumpsKpi() {
  return screen.getByTestId("kpi-total-pumps").textContent;
}

describe("ExecutiveDashboard area filter (LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B)", () => {
  it("offers All Areas plus exactly the backend-authorized areas, with S. Pakning labelled", async () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    await waitFor(() => expect(screen.getByLabelText("Filter by Area").querySelectorAll("option").length).toBe(7));
    const labels = Array.from(screen.getByLabelText("Filter by Area").querySelectorAll("option")).map((o) => o.textContent);
    expect(labels).toEqual(["All Areas", "HOC", "HSC", "S. Pakning", "HCC", "OM", "UTL"]);
  });

  it("offers only HOC to an AREA:HOC user -- options are never a hard-coded list", async () => {
    getLtsaAnalyticsFilters.mockResolvedValue({ authorized_areas: [{ code: "HOC", label: "HOC" }], pumps: [], date_range: {} });
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    await waitFor(() => expect(screen.getByLabelText("Filter by Area").querySelectorAll("option").length).toBe(2));
    expect(screen.queryByRole("option", { name: "HSC" })).toBeNull();
  });

  it("requests the full authorized scope by default (no area parameter)", async () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(await screen.findByTestId("kpi-total-pumps")).toHaveTextContent("230");
    expect(getFleetOverview).toHaveBeenCalledWith({});
    expect(getLtsaAnalyticsExecutive).toHaveBeenCalledWith({});
  });

  it("sends the same selected area to every dashboard request and persists it in ?area=", async () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    await screen.findByTestId("kpi-total-pumps");
    await selectArea("HOC");

    await waitFor(() => expect(totalPumpsKpi()).toContain("54"));
    for (const fn of [getFleetOverview, getFleetReliability, getFleetPowerBI]) {
      expect(fn).toHaveBeenLastCalledWith({ area: "HOC" });
    }
    for (const fn of [getLtsaAnalyticsExecutive, getLtsaAnalyticsSeals, getLtsaAnalyticsMaterials, getLtsaAnalyticsEffectiveness]) {
      expect(fn.mock.calls.at(-1)[0].area).toBe("HOC");
    }
    expect(window.location.search).toBe("?area=HOC");
    expect(window.location.pathname).toBe("/ltsa/dashboard");
    expect(screen.getByTestId("selected-area-badge")).toHaveTextContent("HOC");
  });

  it("restores the area from the URL on load", async () => {
    window.history.pushState({}, "", "/ltsa/dashboard?area=S_PAKNING");
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(await screen.findByTestId("kpi-total-pumps")).toHaveTextContent("10");
    expect(getFleetOverview).toHaveBeenCalledWith({ area: "S_PAKNING" });
  });

  it("clears the previous area's data while the next area loads (no stale HOC values during HSC)", async () => {
    window.history.pushState({}, "", "/ltsa/dashboard?area=HOC");
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(await screen.findByTestId("kpi-total-pumps")).toHaveTextContent("54");

    let resolveOverview;
    getFleetOverview.mockImplementation(() => new Promise((resolve) => { resolveOverview = resolve; }));
    getLtsaAnalyticsExecutive.mockImplementation(() => new Promise(() => {}));
    await selectArea("HSC");

    expect(await screen.findByText(/loading executive dashboard/i)).toBeInTheDocument();
    expect(screen.queryByTestId("kpi-total-pumps")).toBeNull();
    expect(screen.queryByText("54")).toBeNull();

    resolveOverview(overviewFor("HSC"));
    await waitFor(() => expect(screen.queryByText(/loading executive dashboard/i)).toBeNull());
    expect(screen.queryByText("54")).toBeNull();
  });

  it("renders the Unauthorized state on a backend 403 (e.g. ?area=HSC for an AREA:HOC user) and can return to All Areas", async () => {
    window.history.pushState({}, "", "/ltsa/dashboard?area=HSC");
    getFleetOverview.mockImplementation(async (params) => {
      if (areaOf(params) === "HSC") throw forbidden();
      return overviewFor("ALL");
    });
    getLtsaAnalyticsExecutive.mockImplementation(async (params) => {
      if (areaOf(params) === "HSC") throw forbidden();
      return executiveFor("ALL");
    });

    render(<ExecutiveDashboard onNavigate={() => {}} />);

    expect(await screen.findByTestId("dashboard-unauthorized")).toBeInTheDocument();
    expect(screen.getByText("Area not authorized")).toBeInTheDocument();
    expect(screen.queryByTestId("kpi-total-pumps")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Show All Areas" }));
    expect(await screen.findByTestId("kpi-total-pumps")).toHaveTextContent("230");
    expect(window.location.search).toBe("");
  });

  it("renders breakdowns and PM compliance as N/A, never 0 or 100%", async () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    await screen.findByTestId("kpi-total-pumps");
    expect(screen.getByTestId("kpi-breakdowns")).toHaveTextContent("N/A");
    expect(screen.getByTestId("kpi-pm-compliance")).toHaveTextContent("N/A");
    expect(screen.getByTestId("kpi-pm-compliance")).toHaveTextContent("No scheduled PM data");
    expect(screen.getByTestId("kpi-pm-compliance")).not.toHaveTextContent("100");
  });

  it("hides the fleet-wide Seal Inventory panel when the backend withholds it for a scoped view", async () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    await screen.findByTestId("kpi-total-pumps");
    expect(screen.queryByRole("heading", { name: "Seal Inventory" })).toBeNull();
  });

  it("shows an empty state for an authorized area with no pumps", async () => {
    getFleetOverview.mockImplementation(async (params) =>
      areaOf(params) === "UTL" ? { success: true, data: { ...overviewFor("UTL").data, pump_count: 0 } } : overviewFor(areaOf(params))
    );
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    await screen.findByTestId("kpi-total-pumps");
    await selectArea("UTL");
    expect(await screen.findByText("No pumps were found in UTL.")).toBeInTheDocument();
  });

  it("shows the error state when the required overview fails for a non-authorization reason", async () => {
    getFleetOverview.mockRejectedValue(new Error("Fleet overview API unavailable"));
    render(<ExecutiveDashboard onNavigate={() => {}} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Fleet overview API unavailable");
    expect(screen.queryByTestId("dashboard-unauthorized")).toBeNull();
  });
});

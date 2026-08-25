import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AnalyticsWorkspace from "./AnalyticsWorkspace";
import {
  getCMReports,
  getConditionMonitoringReadings,
  getMaintenanceHistory,
  getPMOccurrences,
  getPMSchedules,
  getPumps,
  getWorkOrders,
} from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getPumps: vi.fn(),
  getWorkOrders: vi.fn(),
  getPMSchedules: vi.fn(),
  getCMReports: vi.fn(),
  getMaintenanceHistory: vi.fn(),
  getPMOccurrences: vi.fn(),
  getConditionMonitoringReadings: vi.fn(),
}));

function mockAnalyticsApi({ pumps = [], workOrders = [], pmSchedules = [], cmReports = [], maintenanceHistory = [], pmOccurrences = [], readings = [] } = {}) {
  getPumps.mockResolvedValue(pumps);
  getWorkOrders.mockResolvedValue(workOrders);
  getPMSchedules.mockResolvedValue(pmSchedules);
  getCMReports.mockResolvedValue(cmReports);
  getMaintenanceHistory.mockResolvedValue(maintenanceHistory);
  getPMOccurrences.mockResolvedValue(pmOccurrences);
  getConditionMonitoringReadings.mockResolvedValue(readings);
}

beforeEach(() => {
  vi.clearAllMocks();
  mockAnalyticsApi();
});

describe("Analytics workspace page", () => {
  it("renders the page header and reads production APIs", async () => {
    render(<AnalyticsWorkspace />);

    expect(screen.getByRole("heading", { level: 1, name: "Analytics" })).toBeTruthy();
    await waitFor(() => expect(getPumps).toHaveBeenCalledOnce());
    expect(getWorkOrders).toHaveBeenCalledOnce();
    expect(getPMSchedules).toHaveBeenCalledOnce();
    expect(getCMReports).toHaveBeenCalledOnce();
    expect(getMaintenanceHistory).toHaveBeenCalledOnce();
    expect(getPMOccurrences).toHaveBeenCalledOnce();
    expect(getConditionMonitoringReadings).toHaveBeenCalledOnce();
  });

  it("renders explicit empty state instead of sample fallback when production APIs return empty", async () => {
    render(<AnalyticsWorkspace />);

    expect(await screen.findByText("No analytics data available")).toBeTruthy();
    expect(screen.queryByText("641-P-5")).toBeNull();
    expect(screen.queryByText("Boiler Feedwater Pump 1A")).toBeNull();
  });

  it("renders explicit unavailable state instead of sample fallback when an API fails", async () => {
    getPumps.mockRejectedValue(new Error("API unavailable"));

    render(<AnalyticsWorkspace />);

    expect((await screen.findByRole("alert")).textContent).toBe("Analytics data could not be loaded.");
    expect(screen.queryByText("Sari Wulandari")).toBeNull();
  });

  it("renders supplied real API data without overriding real 211-P-1A identity", async () => {
    mockAnalyticsApi({
      pumps: [
        {
          pump_code: "PUMP-REAL-211",
          tag_number: "211-P-1A",
          name: "FRESH FEED CHARGE PUMP",
          area: "REAKTOR",
          status: "RUNNING",
          criticality: "HIGH",
        },
        {
          pump_code: "PUMP-REAL-220",
          tag_number: "220-P-4A",
          name: "Pump 4A",
          area: "UTILITIES",
          status: "FAULT",
          criticality: "HIGH",
        },
      ],
      workOrders: [
        {
          work_order_code: "WO-REAL-1",
          asset_code: "220-P-4A",
          title: "Inspect pump",
          status: "OPEN",
          priority: "CRITICAL",
          created_at: "2026-07-19T00:00:00Z",
        },
      ],
      pmSchedules: [{ pm_schedule_code: "PM-REAL-1", asset_code: "220-P-4A", status: "OVERDUE" }],
      cmReports: [{ cm_report_code: "CM-REAL-1", asset_code: "220-P-4A", status: "OPEN", severity: "CRITICAL", created_at: "2026-07-19T00:00:00Z" }],
    });

    const { container } = render(<AnalyticsWorkspace />);

    expect(await screen.findByRole("heading", { name: "Are we healthy?" })).toBeTruthy();
    expect(screen.getByText("220-P-4A")).toBeTruthy();
    expect(container.textContent).not.toContain("PM-2001");
    expect(container.textContent).not.toContain("Sari Wulandari");
    expect(container.textContent).not.toContain("Bagus Setiawan");
    expect(container.textContent).not.toContain("Dedi Kurniawan");
    expect(container.textContent).not.toContain("Boiler Feedwater Pump");
    expect(container.textContent).not.toContain("Crude Charge Pump");
    expect(container.textContent).not.toContain("Sour Water Stripper Bottoms Pump");
  });
});

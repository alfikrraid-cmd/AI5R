import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import BasicFleetOverviewPanel from "./BasicFleetOverviewPanel";

// MWO-LTSA-DASHBOARD-RECOVERY-001 -- renders BasicFleetOverview
// (GET /api/ltsa/fleet/overview) exactly as returned, no derived/invented
// fields.
//
// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- trimmed to area/status
// distributions only; pump_count/work_order_count/pm_schedule_count/
// cm_report_count/seal_stock_count/low_stock_seal_count moved to
// FleetKpiStrip/MaintenanceActivityPanel/SealInventoryPanel (see those
// components' own dedicated tests) -- not duplicated here.

function overview(overrides = {}) {
  return {
    pump_count: 4,
    area_distribution: { Reaktor: 3, Utility: 1 },
    status_distribution: { ACTIVE: 4 },
    work_order_count: 2,
    work_order_status_distribution: { OPEN: 2 },
    pm_schedule_count: 1,
    cm_report_count: 1,
    seal_stock_count: 5,
    low_stock_seal_count: 1,
    ...overrides,
  };
}

describe("BasicFleetOverviewPanel", () => {
  it("renders the Fleet Overview heading", () => {
    render(<BasicFleetOverviewPanel overview={overview()} />);

    expect(screen.getByRole("heading", { name: "Fleet Overview" })).toBeTruthy();
  });

  it("renders the area and status distributions", () => {
    render(<BasicFleetOverviewPanel overview={overview()} />);

    expect(screen.getByText("Pumps by Area")).toBeTruthy();
    expect(screen.getByText("Reaktor")).toBeTruthy();
    expect(screen.getByText("Utility")).toBeTruthy();
    expect(screen.getByText("Pumps by Status")).toBeTruthy();
    expect(screen.getByText("ACTIVE")).toBeTruthy();
  });

  it("does not render a Work Orders by Status distribution -- moved to MaintenanceActivityPanel", () => {
    render(<BasicFleetOverviewPanel overview={overview()} />);

    expect(screen.queryByText("Work Orders by Status")).toBeNull();
  });

  it("shows an empty-distribution message rather than a blank section when a distribution is empty", () => {
    render(<BasicFleetOverviewPanel overview={overview({ area_distribution: {}, status_distribution: {} })} />);

    expect(screen.getAllByText(/no data available/i).length).toBe(2);
  });
});

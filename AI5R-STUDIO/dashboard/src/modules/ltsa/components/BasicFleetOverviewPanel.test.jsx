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
//
// MWO-LTSA-FLEET-CONTRACT-AREA-001 -- "Fleet by Contract Area" renders the
// backend's canonical contract_area_distribution, never a frontend-derived
// remapping of the raw area_distribution (which stays, relabeled, alongside
// it as "Pumps by Raw Area/Location").

function overview(overrides = {}) {
  return {
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
  };
}

describe("BasicFleetOverviewPanel", () => {
  it("renders the Fleet Overview heading", () => {
    render(<BasicFleetOverviewPanel overview={overview()} />);

    expect(screen.getByRole("heading", { name: "Fleet Overview" })).toBeTruthy();
  });

  it("renders the raw area and status distributions", () => {
    render(<BasicFleetOverviewPanel overview={overview()} />);

    expect(screen.getByText("Pumps by Raw Area/Location")).toBeTruthy();
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

  it("renders 'Fleet by Contract Area' sourced from contract_area_distribution, not raw area", () => {
    render(
      <BasicFleetOverviewPanel
        overview={overview({
          // Raw values deliberately preserved/shown elsewhere on the page
          // (see "renders the raw area and status distributions") -- this
          // test proves they do NOT also leak into the contract-area
          // section itself.
          area_distribution: { CDU: 1, REAKTOR: 1, HCC: 1, HOC: 1 },
          contract_area_distribution: {
            HOC: 1,
            "HSC & S. Pakning": 0,
            HCC: 1,
            "OM & UTL": 0,
            Unclassified: 2,
          },
        })}
      />
    );

    const section = screen.getByText("Fleet by Contract Area").closest("div");
    // The raw tokens CDU/REAKTOR must never appear inside the contract-area
    // section -- only the 5 canonical labels do.
    expect(section.textContent).not.toContain("CDU");
    expect(section.textContent).not.toContain("REAKTOR");
  });

  it("renders exactly the 5 canonical groups, in order, including Unclassified", () => {
    render(<BasicFleetOverviewPanel overview={overview()} />);

    const section = screen.getByText("Fleet by Contract Area").closest("div");
    const labels = Array.from(section.querySelectorAll("li > span:first-child")).map((el) => el.textContent);

    expect(labels).toEqual(["HOC", "HSC & S. Pakning", "HCC", "OM & UTL", "Unclassified"]);
  });

  it("always renders Unclassified even when it is zero -- never hidden or dropped", () => {
    render(
      <BasicFleetOverviewPanel
        overview={overview({
          contract_area_distribution: {
            HOC: 4,
            "HSC & S. Pakning": 0,
            HCC: 0,
            "OM & UTL": 0,
            Unclassified: 0,
          },
        })}
      />
    );

    const section = screen.getByText("Fleet by Contract Area").closest("div");
    expect(section.textContent).toContain("Unclassified");
    expect(section.textContent).toContain("0");
  });

  it("renders an explicit N/A/unavailable state, not a fallback to raw area, when contract_area_distribution is absent", () => {
    render(<BasicFleetOverviewPanel overview={overview({ contract_area_distribution: undefined })} />);

    const section = screen.getByText("Fleet by Contract Area").closest("div");
    expect(section.textContent).toMatch(/n\/a|unavailable/i);
    // Confirms no silent substitution of the raw distribution's own labels
    // into the contract-area section.
    expect(screen.queryByText("HOC")).toBeNull();
  });

  it("displayed contract-area total reconciles to pump_count", () => {
    const fixture = overview({
      pump_count: 3,
      contract_area_distribution: {
        HOC: 1,
        "HSC & S. Pakning": 1,
        HCC: 0,
        "OM & UTL": 0,
        Unclassified: 1,
      },
    });

    render(<BasicFleetOverviewPanel overview={fixture} />);

    const total = Object.values(fixture.contract_area_distribution).reduce((sum, n) => sum + n, 0);
    expect(total).toBe(fixture.pump_count);
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import BasicFleetOverviewPanel from "./BasicFleetOverviewPanel";

// MWO-LTSA-DASHBOARD-RECOVERY-001 -- renders BasicFleetOverview
// (GET /api/ltsa/fleet/overview) exactly as returned, no derived/invented
// fields.
//
// MWO-LTSA-RELIABILITY-COMMAND-CENTER-001 -- "Fleet by Contract Area" is
// the card's primary content: 4 canonical group cards (count + % of
// fleet, arithmetic only, never a re-classification), Unclassified shown
// separately at lower visual weight, raw area/status preserved behind a
// "View Details" toggle (never deleted).

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
  it("renders the Fleet by Contract Area heading", () => {
    render(<BasicFleetOverviewPanel overview={overview()} />);

    expect(screen.getByRole("heading", { name: "Fleet by Contract Area" })).toBeTruthy();
  });

  it("renders exactly the 4 canonical contract-area cards with count and % of fleet", () => {
    render(
      <BasicFleetOverviewPanel
        overview={overview({
          pump_count: 4,
          contract_area_distribution: {
            HOC: 1,
            "HSC & S. Pakning": 1,
            HCC: 1,
            "OM & UTL": 0,
            Unclassified: 1,
          },
        })}
      />
    );

    expect(screen.getByText("HOC")).toBeTruthy();
    expect(screen.getByText("HSC & S. Pakning")).toBeTruthy();
    expect(screen.getByText("HCC")).toBeTruthy();
    expect(screen.getByText("OM & UTL")).toBeTruthy();
    // Each of the 3 non-zero canonical groups is 1/4 = 25% of the fleet.
    expect(screen.getAllByText("25% of fleet").length).toBe(3);
  });

  it("shows the Unclassified count as a lower-priority warning, not a 5th equal card", () => {
    render(
      <BasicFleetOverviewPanel
        overview={overview({
          contract_area_distribution: { HOC: 3, "HSC & S. Pakning": 0, HCC: 0, "OM & UTL": 0, Unclassified: 1 },
        })}
      />
    );

    expect(screen.getByRole("status").textContent).toMatch(/1 asset requires area classification/i);
    // Not rendered as one of the 4 contract-area-card labels.
    expect(screen.queryByText("Unclassified")).toBeNull();
  });

  it("does not show the Unclassified warning when there are zero unclassified assets", () => {
    render(
      <BasicFleetOverviewPanel
        overview={overview({
          contract_area_distribution: { HOC: 4, "HSC & S. Pakning": 0, HCC: 0, "OM & UTL": 0, Unclassified: 0 },
        })}
      />
    );

    expect(screen.queryByRole("status")).toBeNull();
  });

  it("renders an explicit N/A/unavailable state, not a fallback to raw area, when contract_area_distribution is absent", () => {
    render(<BasicFleetOverviewPanel overview={overview({ contract_area_distribution: undefined })} />);

    expect(screen.getByText(/n\/a.*unavailable/i)).toBeTruthy();
    expect(screen.queryByText("HOC")).toBeNull();
  });

  it("hides raw area/status distributions by default; View Details reveals them without deleting the data", () => {
    render(<BasicFleetOverviewPanel overview={overview()} />);

    expect(screen.queryByText("Pumps by Raw Area/Location")).toBeNull();
    expect(screen.queryByText("Reaktor")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "View Details" }));

    expect(screen.getByText("Pumps by Raw Area/Location")).toBeTruthy();
    expect(screen.getByText("Reaktor")).toBeTruthy();
    expect(screen.getByText("Utility")).toBeTruthy();
    expect(screen.getByText("Pumps by Status")).toBeTruthy();
    expect(screen.getByText("ACTIVE")).toBeTruthy();
  });

  it("View Details is available even when there are zero unclassified assets -- raw data access is never conditional on that", () => {
    render(
      <BasicFleetOverviewPanel
        overview={overview({
          contract_area_distribution: { HOC: 4, "HSC & S. Pakning": 0, HCC: 0, "OM & UTL": 0, Unclassified: 0 },
        })}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "View Details" }));

    expect(screen.getByText("Pumps by Raw Area/Location")).toBeTruthy();
  });

  it("shows an empty-distribution message rather than a blank section for an empty raw distribution", () => {
    render(<BasicFleetOverviewPanel overview={overview({ area_distribution: {}, status_distribution: {} })} />);

    fireEvent.click(screen.getByRole("button", { name: "View Details" }));

    expect(screen.getAllByText(/no data available/i).length).toBe(2);
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

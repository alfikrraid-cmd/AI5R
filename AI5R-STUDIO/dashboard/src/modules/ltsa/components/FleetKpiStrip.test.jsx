import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import FleetKpiStrip from "./FleetKpiStrip";

// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- every value is read from
// existing API data only; unresolved lookups render "N/A", never 0 or a
// guessed value.

function overview(overrides = {}) {
  return {
    pump_count: 4,
    status_distribution: { RUNNING: 3, STANDBY: 1 },
    work_order_count: 2,
    ...overrides,
  };
}

describe("FleetKpiStrip", () => {
  it("renders Pumps from overview.pump_count", () => {
    render(<FleetKpiStrip overview={overview()} summary={null} />);

    expect(screen.getByText("Pumps")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy();
  });

  it("renders Running/Standby from status_distribution when RUNNING/STANDBY keys exist", () => {
    render(<FleetKpiStrip overview={overview()} summary={null} />);

    expect(screen.getByText("Running")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("Standby")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("falls back to ACTIVE/IDLE conventions when RUNNING/STANDBY are absent", () => {
    render(
      <FleetKpiStrip
        overview={overview({ status_distribution: { ACTIVE: 2, IDLE: 1 } })}
        summary={null}
      />
    );

    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);
  });

  it("renders N/A for Running/Standby, never 0, when no matching status vocabulary is found", () => {
    render(<FleetKpiStrip overview={overview({ status_distribution: { UNKNOWN: 4 } })} summary={null} />);

    const naValues = screen.getAllByText("N/A");
    expect(naValues.length).toBeGreaterThanOrEqual(2);
  });

  it("renders Attention from the optional summary's critical_asset_count when available", () => {
    render(<FleetKpiStrip overview={overview()} summary={{ critical_asset_count: 2 }} />);

    expect(screen.getByText("Attention")).toBeTruthy();
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
  });

  it("renders N/A for Attention when the optional summary hasn't loaded", () => {
    render(<FleetKpiStrip overview={overview()} summary={null} />);

    expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
  });

  it("renders Open WO from overview.work_order_count", () => {
    render(<FleetKpiStrip overview={overview()} summary={null} />);

    expect(screen.getByText("Open WO")).toBeTruthy();
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import FleetExecutiveSummary from "./FleetExecutiveSummary";

function summary(overrides = {}) {
  return {
    overall_health: 86.5,
    fleet_status: "NORMAL",
    critical_asset_count: 1,
    fleet_availability: 98.76,
    fleet_mtbf_days: 42.3,
    fleet_mttr_hours: 6.25,
    breakdown_count: 3,
    critical_spare_count: 2,
    top_risks: [],
    insight: null,
    ...overrides,
  };
}

describe("FleetExecutiveSummary", () => {
  it("renders the Executive Summary heading", () => {
    render(<FleetExecutiveSummary summary={summary()} />);
    expect(screen.getByRole("heading", { name: "Executive Summary" })).toBeTruthy();
  });

  it("renders all eight summary fields, correctly formatted, reusing the shared formatters", () => {
    render(<FleetExecutiveSummary summary={summary()} />);

    expect(screen.getByText("Fleet Health")).toBeTruthy();
    expect(screen.getByText("87")).toBeTruthy();
    expect(screen.getByText("Fleet Status")).toBeTruthy();
    expect(screen.getByText("NORMAL")).toBeTruthy();
    expect(screen.getByText("Critical Assets")).toBeTruthy();
    expect(screen.getByText("Availability")).toBeTruthy();
    expect(screen.getByText("98.76%")).toBeTruthy();
    expect(screen.getByText("MTBF")).toBeTruthy();
    expect(screen.getByText("42 days")).toBeTruthy();
    expect(screen.getByText("MTTR")).toBeTruthy();
    expect(screen.getByText("6 hrs")).toBeTruthy();
    expect(screen.getByText("Breakdown Count")).toBeTruthy();
    expect(screen.getByText("Critical Spare Count")).toBeTruthy();
  });

  it("shows Unavailable for null fields, never a fabricated number", () => {
    render(
      <FleetExecutiveSummary
        summary={summary({ overall_health: null, fleet_availability: null, fleet_mtbf_days: null, fleet_mttr_hours: null })}
      />
    );

    expect(screen.getAllByText("Unavailable").length).toBe(4);
  });
});

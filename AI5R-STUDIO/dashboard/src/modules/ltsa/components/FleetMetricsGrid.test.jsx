import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import FleetMetricsGrid from "./FleetMetricsGrid";

function props(overrides = {}) {
  return {
    availability: 98.76,
    mtbfDays: 42.3,
    mttrHours: 6.25,
    pumpCount: 4,
    breakdownCount: 3,
    criticalSpareCount: 2,
    ...overrides,
  };
}

describe("FleetMetricsGrid", () => {
  it("renders all six required metric cards", () => {
    render(<FleetMetricsGrid {...props()} />);

    expect(screen.getByText("Availability")).toBeTruthy();
    expect(screen.getByText("MTBF")).toBeTruthy();
    expect(screen.getByText("MTTR")).toBeTruthy();
    expect(screen.getByText("Pump Count")).toBeTruthy();
    expect(screen.getByText("Breakdown Count")).toBeTruthy();
    expect(screen.getByText("Critical Spare Count")).toBeTruthy();
  });

  it("formats Availability as a percentage", () => {
    render(<FleetMetricsGrid {...props({ availability: 98.76 })} />);
    expect(screen.getByText("98.76%")).toBeTruthy();
  });

  it("formats MTBF in days and MTTR in hours", () => {
    render(<FleetMetricsGrid {...props({ mtbfDays: 42.3, mttrHours: 6.25 })} />);
    expect(screen.getByText("42 days")).toBeTruthy();
    expect(screen.getByText("6 hrs")).toBeTruthy();
  });

  it("renders Pump Count, Breakdown Count, and Critical Spare Count as plain integers", () => {
    render(<FleetMetricsGrid {...props({ pumpCount: 4, breakdownCount: 3, criticalSpareCount: 2 })} />);
    expect(screen.getByText("4")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("shows Unavailable for Availability/MTBF/MTTR when null, never a fabricated number", () => {
    render(<FleetMetricsGrid {...props({ availability: null, mtbfDays: null, mttrHours: null })} />);
    expect(screen.getAllByText("Unavailable").length).toBe(3);
  });
});

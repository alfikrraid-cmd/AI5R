import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MaintenanceActivityPanel from "./MaintenanceActivityPanel";

function overview(overrides = {}) {
  return {
    pm_schedule_count: 3,
    cm_report_count: 2,
    work_order_count: 5,
    work_order_status_distribution: { OPEN: 3, CLOSED: 2 },
    ...overrides,
  };
}

describe("MaintenanceActivityPanel", () => {
  it("renders PM Schedules, CM Reports, and Work Orders counts", () => {
    render(<MaintenanceActivityPanel overview={overview()} />);

    expect(screen.getByText("PM Schedules")).toBeTruthy();
    expect(screen.getAllByText("3").length).toBeGreaterThan(0);
    expect(screen.getByText("CM Reports")).toBeTruthy();
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
    expect(screen.getByText("Work Orders")).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();
  });

  it("renders the work order status distribution", () => {
    render(<MaintenanceActivityPanel overview={overview()} />);

    expect(screen.getByText("OPEN")).toBeTruthy();
    expect(screen.getByText("CLOSED")).toBeTruthy();
  });

  it("shows a disclosed empty message, not a blank section, when no status data exists", () => {
    render(<MaintenanceActivityPanel overview={overview({ work_order_status_distribution: {} })} />);

    expect(screen.getByText(/no work order status data available/i)).toBeTruthy();
  });

  it("never fabricates a count -- zero renders as 0, not hidden or guessed", () => {
    render(
      <MaintenanceActivityPanel
        overview={overview({ pm_schedule_count: 0, cm_report_count: 0, work_order_count: 0 })}
      />
    );

    expect(screen.getAllByText("0").length).toBe(3);
  });
});

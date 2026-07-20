import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MaintenanceHealthPanel from "./MaintenanceHealthPanel";

const HEALTH = {
  pmComplianceRate: 63,
  totalPM: 8,
  overduePM: 3,
  totalWorkOrders: 8,
  openWorkOrders: 7,
  closedWorkOrders: 1,
  cmStatusCounts: { OPEN: 2, IN_PROGRESS: 2, RESOLVED: 2, CLOSED: 2 },
};

describe("MaintenanceHealthPanel", () => {
  it("renders the PM compliance progress bar with its rate and detail", () => {
    render(<MaintenanceHealthPanel health={HEALTH} />);

    expect(screen.getByRole("heading", { name: "Maintenance Health" })).toBeTruthy();
    expect(screen.getByText(/PM Compliance — 63%/)).toBeTruthy();
    expect(screen.getByText(/5 of 8 not overdue/)).toBeTruthy();
  });

  it("renders the work order open/closed progress bar", () => {
    render(<MaintenanceHealthPanel health={HEALTH} />);

    expect(screen.getByText(/1 closed \/ 7 open \(of 8\)/)).toBeTruthy();
  });

  it("renders a badge per corrective maintenance status with its count", () => {
    render(<MaintenanceHealthPanel health={HEALTH} />);

    expect(screen.getByText("Open: 2")).toBeTruthy();
    expect(screen.getByText("In Progress: 2")).toBeTruthy();
    expect(screen.getByText("Resolved: 2")).toBeTruthy();
    expect(screen.getByText("Closed: 2")).toBeTruthy();
  });
});

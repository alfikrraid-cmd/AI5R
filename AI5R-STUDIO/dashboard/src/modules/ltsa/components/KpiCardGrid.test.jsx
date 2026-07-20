import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import KpiCardGrid from "./KpiCardGrid";

const KPIS = {
  openWorkOrders: 7,
  overduePM: 3,
  upcomingPM: 2,
  openCorrectiveMaintenance: 4,
  criticalAssets: 4,
  recentMaintenanceActivity: 11,
};

describe("KpiCardGrid", () => {
  it("renders all six executive KPI cards with their derived values", () => {
    render(<KpiCardGrid kpis={KPIS} />);

    expect(screen.getByText("Open Work Orders")).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText("Overdue PM")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("Upcoming PM")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText("Open Corrective Maintenance")).toBeTruthy();
    expect(screen.getByText("Critical Assets")).toBeTruthy();
    expect(screen.getByText("Recent Maintenance Activity")).toBeTruthy();
    expect(screen.getByText("11")).toBeTruthy();
  });
});

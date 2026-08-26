import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import UpcomingMaintenanceList from "./UpcomingMaintenanceList";

const SCHEDULES = [
  {
    id: "PM-2002",
    equipmentTag: "112-P-3",
    procedure: "Bearing Housing Inspection",
    nextDue: "2026-07-24",
    assignedTechnician: "Bagus Setiawan",
    status: "OVERDUE",
  },
  {
    id: "PM-2001",
    equipmentTag: "211-P-1A",
    procedure: "Lubrication & Vibration Check",
    nextDue: "2026-07-24",
    assignedTechnician: "Sari Wulandari",
    status: "ACTIVE",
  },
];

describe("UpcomingMaintenanceList", () => {
  it("renders a row per upcoming PM schedule", () => {
    render(<UpcomingMaintenanceList schedules={SCHEDULES} />);

    expect(screen.getByRole("heading", { name: "Upcoming Maintenance" })).toBeTruthy();
    expect(screen.getByText("Bearing Housing Inspection")).toBeTruthy();
    expect(screen.getByText(/PM-2002/)).toBeTruthy();
    expect(screen.getByText("Overdue")).toBeTruthy();
    expect(screen.getByText("Active")).toBeTruthy();
  });

  it("renders an empty state when nothing is due", () => {
    render(<UpcomingMaintenanceList schedules={[]} />);

    expect(screen.getByText(/nothing due soon/i)).toBeTruthy();
  });
});

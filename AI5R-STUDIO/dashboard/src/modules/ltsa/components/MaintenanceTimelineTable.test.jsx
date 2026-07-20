import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MaintenanceTimelineTable from "./MaintenanceTimelineTable";

const EVENTS = [
  {
    id: "WO-1001",
    type: "WO",
    date: "2026-07-18",
    title: "Seal replacement — repeat failures",
    status: "OPEN",
    assignedTechnician: "Dedi Kurniawan",
  },
  {
    id: "PM-2008",
    type: "PM",
    date: "2025-12-10",
    title: "Seal Chamber Condition Check",
    status: "OVERDUE",
    assignedTechnician: "Dedi Kurniawan",
  },
];

describe("MaintenanceTimelineTable", () => {
  it("renders the timeline columns", () => {
    render(<MaintenanceTimelineTable events={EVENTS} selectedId={null} onSelect={() => {}} />);

    ["Date", "Type", "Event", "Status", "Assigned Technician"].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per event with a type badge and a status badge", () => {
    render(<MaintenanceTimelineTable events={EVENTS} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("WO-1001")).toBeTruthy();
    expect(screen.getByText("Work Order")).toBeTruthy();
    expect(screen.getByText("PM-2008")).toBeTruthy();
    expect(screen.getByText("PM")).toBeTruthy();
    expect(screen.getByText("Open")).toBeTruthy();
    expect(screen.getByText("Overdue")).toBeTruthy();
  });

  it("calls onSelect with the clicked event's id", () => {
    const onSelect = vi.fn();
    render(<MaintenanceTimelineTable events={EVENTS} selectedId={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("PM-2008"));

    expect(onSelect).toHaveBeenCalledWith("PM-2008");
  });

  it("marks the selected row", () => {
    render(<MaintenanceTimelineTable events={EVENTS} selectedId="PM-2008" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });

  it("marks table rows as keyboard-focusable and activates onSelect via Enter", () => {
    const onSelect = vi.fn();
    render(<MaintenanceTimelineTable events={EVENTS} selectedId={null} onSelect={onSelect} />);

    const rows = screen.getAllByRole("row");
    expect(rows[1].getAttribute("tabIndex")).toBe("0");

    fireEvent.keyDown(rows[1], { key: "Enter" });

    expect(onSelect).toHaveBeenCalledWith("WO-1001");
  });

  it("renders an empty state instead of a bare table when no events match", () => {
    render(<MaintenanceTimelineTable events={[]} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText(/no history matches/i)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});

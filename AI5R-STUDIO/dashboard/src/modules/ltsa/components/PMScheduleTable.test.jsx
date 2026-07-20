import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PMScheduleTable from "./PMScheduleTable";

const PM_SCHEDULES = [
  {
    id: "PM-2001",
    equipmentTag: "211-P-1A",
    area: "Boiler House",
    procedure: "Lubrication & Vibration Check",
    frequency: "MONTHLY",
    nextDue: "2026-07-24",
    lastPerformed: "2026-06-02",
    assignedTechnician: "Sari Wulandari",
    status: "DUE_SOON",
  },
  {
    id: "PM-2002",
    equipmentTag: "112-P-3",
    area: "CDU",
    procedure: "Bearing Housing Inspection",
    frequency: "RUNTIME_BASED",
    nextDue: "2026-07-24",
    lastPerformed: "2025-11-18",
    assignedTechnician: "Bagus Setiawan",
    status: "OVERDUE",
  },
];

describe("PMScheduleTable", () => {
  it("renders the PM schedule columns", () => {
    render(<PMScheduleTable pmSchedules={PM_SCHEDULES} selectedId={null} onSelect={() => {}} />);

    [
      "PM ID",
      "Equipment",
      "Frequency",
      "Next Due",
      "Last Performed",
      "Assigned Technician",
      "Status",
    ].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per PM schedule with id/procedure grouped under PM ID", () => {
    render(<PMScheduleTable pmSchedules={PM_SCHEDULES} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("PM-2001")).toBeTruthy();
    expect(screen.getByText("Bearing Housing Inspection")).toBeTruthy();
    expect(screen.getByText("112-P-3")).toBeTruthy();
  });

  it("renders a human-readable frequency badge", () => {
    render(<PMScheduleTable pmSchedules={PM_SCHEDULES} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("Monthly")).toBeTruthy();
    expect(screen.getByText("Runtime-based")).toBeTruthy();
  });

  it("calls onSelect with the clicked PM schedule's id", () => {
    const onSelect = vi.fn();
    render(<PMScheduleTable pmSchedules={PM_SCHEDULES} selectedId={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("PM-2002"));

    expect(onSelect).toHaveBeenCalledWith("PM-2002");
  });

  it("marks the selected row", () => {
    render(<PMScheduleTable pmSchedules={PM_SCHEDULES} selectedId="PM-2002" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });

  it("renders a status badge for each PM schedule", () => {
    render(<PMScheduleTable pmSchedules={PM_SCHEDULES} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("Due Soon")).toBeTruthy();
    expect(screen.getByText("Overdue")).toBeTruthy();
  });

  it("renders a fallback when a PM schedule has not yet been performed", () => {
    render(
      <PMScheduleTable
        pmSchedules={[{ ...PM_SCHEDULES[0], lastPerformed: null }]}
        selectedId={null}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText("Not yet performed")).toBeTruthy();
  });

  it("renders an empty state instead of a bare table when no PM schedules match", () => {
    render(<PMScheduleTable pmSchedules={[]} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText(/no pm schedules match/i)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("marks table rows as keyboard-focusable and activates onSelect via Enter", () => {
    const onSelect = vi.fn();
    render(<PMScheduleTable pmSchedules={PM_SCHEDULES} selectedId={null} onSelect={onSelect} />);

    const rows = screen.getAllByRole("row");
    expect(rows[1].getAttribute("tabIndex")).toBe("0");

    fireEvent.keyDown(rows[1], { key: "Enter" });

    expect(onSelect).toHaveBeenCalledWith("PM-2001");
  });
});

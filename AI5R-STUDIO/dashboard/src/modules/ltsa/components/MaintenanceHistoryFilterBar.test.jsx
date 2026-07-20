import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MaintenanceHistoryFilterBar from "./MaintenanceHistoryFilterBar";

const BASE_PROPS = {
  dateFrom: "",
  onDateFromChange: () => {},
  dateTo: "",
  onDateToChange: () => {},
  eventTypeFilter: "ALL",
  onEventTypeFilterChange: () => {},
  statusFilter: "ALL",
  onStatusFilterChange: () => {},
  statusOptions: ["OPEN", "OVERDUE"],
  technicianFilter: "ALL",
  onTechnicianFilterChange: () => {},
  technicianOptions: ["Dedi Kurniawan", "Sari Wulandari"],
};

describe("MaintenanceHistoryFilterBar", () => {
  it("renders date range, event type, status, and technician controls", () => {
    render(<MaintenanceHistoryFilterBar {...BASE_PROPS} />);

    expect(screen.getByLabelText("Date From")).toBeTruthy();
    expect(screen.getByLabelText("Date To")).toBeTruthy();
    expect(screen.getByLabelText("Event Type")).toBeTruthy();
    expect(screen.getByLabelText("Status")).toBeTruthy();
    expect(screen.getByLabelText("Assigned Technician")).toBeTruthy();
  });

  it("renders every event type option with humanized labels", () => {
    render(<MaintenanceHistoryFilterBar {...BASE_PROPS} />);

    expect(screen.getByRole("option", { name: "All Types" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "PM" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "CM" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Work Order" })).toBeTruthy();
  });

  it("renders status options with humanized labels", () => {
    render(<MaintenanceHistoryFilterBar {...BASE_PROPS} />);

    expect(screen.getByRole("option", { name: "Open" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Overdue" })).toBeTruthy();
  });

  it("renders every technician option", () => {
    render(<MaintenanceHistoryFilterBar {...BASE_PROPS} />);

    expect(screen.getByRole("option", { name: "Dedi Kurniawan" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Sari Wulandari" })).toBeTruthy();
  });

  it("calls the change handlers", () => {
    const onDateFromChange = vi.fn();
    const onDateToChange = vi.fn();
    const onEventTypeFilterChange = vi.fn();
    const onStatusFilterChange = vi.fn();
    const onTechnicianFilterChange = vi.fn();

    render(
      <MaintenanceHistoryFilterBar
        {...BASE_PROPS}
        onDateFromChange={onDateFromChange}
        onDateToChange={onDateToChange}
        onEventTypeFilterChange={onEventTypeFilterChange}
        onStatusFilterChange={onStatusFilterChange}
        onTechnicianFilterChange={onTechnicianFilterChange}
      />
    );

    fireEvent.change(screen.getByLabelText("Date From"), { target: { value: "2026-01-01" } });
    fireEvent.change(screen.getByLabelText("Date To"), { target: { value: "2026-12-31" } });
    fireEvent.change(screen.getByLabelText("Event Type"), { target: { value: "PM" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "OVERDUE" } });
    fireEvent.change(screen.getByLabelText("Assigned Technician"), {
      target: { value: "Dedi Kurniawan" },
    });

    expect(onDateFromChange).toHaveBeenCalledWith("2026-01-01");
    expect(onDateToChange).toHaveBeenCalledWith("2026-12-31");
    expect(onEventTypeFilterChange).toHaveBeenCalledWith("PM");
    expect(onStatusFilterChange).toHaveBeenCalledWith("OVERDUE");
    expect(onTechnicianFilterChange).toHaveBeenCalledWith("Dedi Kurniawan");
  });
});

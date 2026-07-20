import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MaintenanceHistory from "./MaintenanceHistory";

function selectAsset(tag) {
  fireEvent.change(screen.getByLabelText("Select Asset"), { target: { value: tag } });
}

describe("Maintenance History workspace page", () => {
  it("renders the page header", () => {
    render(<MaintenanceHistory />);

    expect(screen.getByRole("heading", { name: "Maintenance History" })).toBeTruthy();
  });

  it("shows an empty state before any asset is selected", () => {
    render(<MaintenanceHistory />);

    expect(screen.getByText(/no asset selected/i)).toBeTruthy();
  });

  it("shows the Asset Summary and merged timeline once a pump is selected", () => {
    render(<MaintenanceHistory />);

    selectAsset("641-P-5");

    expect(screen.getByRole("heading", { name: "Asset Summary" })).toBeTruthy();
    expect(screen.getByText("WO-1001")).toBeTruthy();
    expect(screen.getByText("CM-3001")).toBeTruthy();
    expect(screen.getByText("PM-2008")).toBeTruthy();
  });

  it("shows an empty state in the detail panel before any event is selected", () => {
    render(<MaintenanceHistory />);

    selectAsset("641-P-5");

    expect(screen.getByText(/no event selected/i)).toBeTruthy();
  });

  it("shows event details when a timeline row is clicked", () => {
    render(<MaintenanceHistory />);

    selectAsset("641-P-5");
    fireEvent.click(screen.getByText("PM-2008"));

    expect(screen.getByRole("heading", { name: "Preventive Maintenance Details" })).toBeTruthy();
  });

  it("filters the timeline by event type", () => {
    render(<MaintenanceHistory />);

    selectAsset("641-P-5");
    fireEvent.change(screen.getByLabelText("Event Type"), { target: { value: "WO" } });

    expect(screen.getByText("WO-1001")).toBeTruthy();
    expect(screen.queryByText("CM-3001")).toBeNull();
    expect(screen.queryByText("PM-2008")).toBeNull();
  });

  it("filters the timeline by status", () => {
    render(<MaintenanceHistory />);

    selectAsset("641-P-5");
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "OVERDUE" } });

    expect(screen.getByText("PM-2008")).toBeTruthy();
    expect(screen.queryByText("WO-1001")).toBeNull();
    expect(screen.queryByText("CM-3001")).toBeNull();
  });

  it("filters the timeline by assigned technician", () => {
    render(<MaintenanceHistory />);

    selectAsset("641-P-5");
    fireEvent.change(screen.getByLabelText("Assigned Technician"), {
      target: { value: "Dedi Kurniawan" },
    });

    expect(screen.getByText("WO-1001")).toBeTruthy();
    expect(screen.getByText("CM-3001")).toBeTruthy();
    expect(screen.getByText("PM-2008")).toBeTruthy();
  });

  it("filters the timeline by date range", () => {
    render(<MaintenanceHistory />);

    selectAsset("641-P-5");
    fireEvent.change(screen.getByLabelText("Date From"), { target: { value: "2026-01-01" } });

    expect(screen.getByText("WO-1001")).toBeTruthy();
    expect(screen.getByText("CM-3001")).toBeTruthy();
    expect(screen.queryByText("PM-2008")).toBeNull();
  });

  it("resets filters and selection when a different asset is chosen", () => {
    render(<MaintenanceHistory />);

    selectAsset("641-P-5");
    fireEvent.click(screen.getByText("PM-2008"));
    fireEvent.change(screen.getByLabelText("Event Type"), { target: { value: "PM" } });

    selectAsset("211-P-1A");

    expect(screen.getByLabelText("Event Type").value).toBe("ALL");
    expect(screen.getByText(/no event selected/i)).toBeTruthy();
  });
});

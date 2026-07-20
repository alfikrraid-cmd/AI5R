import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CMReportTable from "./CMReportTable";

const CM_REPORTS = [
  {
    id: "CM-3001",
    equipmentTag: "641-P-5",
    area: "SWS Unit",
    failureCategory: "SEAL_FAILURE",
    failureDescription: "Third mechanical seal failure in 90 days.",
    severity: "CRITICAL",
    priority: "HIGH",
    downtimeHours: 18,
    assignedTechnician: "Dedi Kurniawan",
    status: "IN_PROGRESS",
  },
  {
    id: "CM-3004",
    equipmentTag: "211-P-1A",
    area: "Boiler House",
    failureCategory: "INSTRUMENTATION",
    failureDescription: "Vibration sensor reading spike.",
    severity: "MINOR",
    priority: "LOW",
    downtimeHours: 1,
    assignedTechnician: "Sari Wulandari",
    status: "CLOSED",
  },
];

describe("CMReportTable", () => {
  it("renders the corrective maintenance columns", () => {
    render(<CMReportTable cmReports={CM_REPORTS} selectedId={null} onSelect={() => {}} />);

    [
      "CM ID",
      "Equipment",
      "Failure Category",
      "Severity",
      "Priority",
      "Downtime",
      "Assigned Technician",
      "Status",
    ].forEach((header) => {
      expect(screen.getByRole("columnheader", { name: header })).toBeTruthy();
    });
  });

  it("renders one row per report with id/failure description grouped under CM ID", () => {
    render(<CMReportTable cmReports={CM_REPORTS} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("CM-3001")).toBeTruthy();
    expect(screen.getByText("Vibration sensor reading spike.")).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
  });

  it("renders a human-readable failure category", () => {
    render(<CMReportTable cmReports={CM_REPORTS} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("Seal Failure")).toBeTruthy();
    expect(screen.getByText("Instrumentation")).toBeTruthy();
  });

  it("renders downtime with an hours suffix", () => {
    render(<CMReportTable cmReports={CM_REPORTS} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("18 hrs")).toBeTruthy();
    expect(screen.getByText("1 hrs")).toBeTruthy();
  });

  it("calls onSelect with the clicked report's id", () => {
    const onSelect = vi.fn();
    render(<CMReportTable cmReports={CM_REPORTS} selectedId={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("CM-3004"));

    expect(onSelect).toHaveBeenCalledWith("CM-3004");
  });

  it("marks the selected row", () => {
    render(<CMReportTable cmReports={CM_REPORTS} selectedId="CM-3004" onSelect={() => {}} />);

    const rows = screen.getAllByRole("row");
    expect(rows[2].getAttribute("aria-selected")).toBe("true");
  });

  it("renders a severity badge, a priority badge, and a status badge for each report", () => {
    render(<CMReportTable cmReports={CM_REPORTS} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText("CRITICAL")).toBeTruthy();
    expect(screen.getByText("MINOR")).toBeTruthy();
    expect(screen.getByText("LOW")).toBeTruthy();
    expect(screen.getByText("In Progress")).toBeTruthy();
    expect(screen.getByText("Closed")).toBeTruthy();
  });

  it("renders an empty state instead of a bare table when no reports match", () => {
    render(<CMReportTable cmReports={[]} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText(/no corrective maintenance reports match/i)).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("marks table rows as keyboard-focusable and activates onSelect via Enter", () => {
    const onSelect = vi.fn();
    render(<CMReportTable cmReports={CM_REPORTS} selectedId={null} onSelect={onSelect} />);

    const rows = screen.getAllByRole("row");
    expect(rows[1].getAttribute("tabIndex")).toBe("0");

    fireEvent.keyDown(rows[1], { key: "Enter" });

    expect(onSelect).toHaveBeenCalledWith("CM-3001");
  });
});

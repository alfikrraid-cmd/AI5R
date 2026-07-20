import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ReportsWorkspace from "./ReportsWorkspace";

describe("ReportsWorkspace", () => {
  it("renders a tab for every report, using full report names to avoid clashing with LTSAWorkspace's own tabs", () => {
    render(<ReportsWorkspace />);

    expect(screen.getByRole("tab", { name: "Executive Summary Report" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Pump History Report" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Work Order Report" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Preventive Maintenance Report" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Corrective Maintenance Report" })).toBeTruthy();
  });

  it("defaults to the Executive Summary report", () => {
    render(<ReportsWorkspace />);

    expect(
      screen.getByRole("tab", { name: "Executive Summary Report" }).getAttribute("aria-selected")
    ).toBe("true");
    expect(screen.getByRole("heading", { name: "Executive Summary Report" })).toBeTruthy();
  });

  it("switches to the Pump History report when its tab is clicked", () => {
    render(<ReportsWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Pump History Report" }));

    expect(screen.getByRole("heading", { name: "Pump History Report" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Executive Summary Report" })).toBeNull();
  });

  it("switches to the Work Order report when its tab is clicked", () => {
    render(<ReportsWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Work Order Report" }));

    expect(screen.getByRole("heading", { name: "Work Order Report" })).toBeTruthy();
  });

  it("switches to the Preventive Maintenance report when its tab is clicked", () => {
    render(<ReportsWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Preventive Maintenance Report" }));

    expect(screen.getByRole("heading", { name: "Preventive Maintenance Report" })).toBeTruthy();
  });

  it("switches to the Corrective Maintenance report when its tab is clicked", () => {
    render(<ReportsWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Corrective Maintenance Report" }));

    expect(screen.getByRole("heading", { name: "Corrective Maintenance Report" })).toBeTruthy();
  });
});

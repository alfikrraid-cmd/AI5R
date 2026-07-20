import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CM from "./CM";
import sampleCMReports from "../data/sampleCMReports";

describe("Corrective Maintenance workspace page", () => {
  it("renders the page header", () => {
    render(<CM />);

    expect(screen.getByRole("heading", { name: "Corrective Maintenance Workspace" })).toBeTruthy();
  });

  it("renders every sample CM report in the list", () => {
    render(<CM />);

    sampleCMReports.forEach((cm) => {
      expect(screen.getByText(cm.id)).toBeTruthy();
    });
  });

  it("shows an empty state in the detail panel before any report is selected", () => {
    render(<CM />);

    expect(screen.getByText(/no corrective maintenance report selected/i)).toBeTruthy();
  });

  it("shows the selected report's detail when a list row is clicked", () => {
    render(<CM />);

    fireEvent.click(screen.getByText("CM-3003"));

    expect(
      screen.getByRole("heading", {
        name: "Excessive wear-plate erosion found during scheduled inspection, below minimum thickness.",
      })
    ).toBeTruthy();
  });

  it("filters the list by search text", () => {
    render(<CM />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "bearing" } });

    expect(screen.getByText("CM-3005")).toBeTruthy();
    expect(screen.queryByText("CM-3001")).toBeNull();
  });

  it("filters the list by status", () => {
    render(<CM />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "CLOSED" } });

    expect(screen.getByText("CM-3004")).toBeTruthy();
    expect(screen.getByText("CM-3006")).toBeTruthy();
    expect(screen.queryByText("CM-3001")).toBeNull();
  });

  it("shows an empty state in the list when no report matches the search", () => {
    render(<CM />);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "no-such-report-xyz" } });

    expect(screen.getByText(/no corrective maintenance reports match/i)).toBeTruthy();
  });

  it("opens the Create Corrective Maintenance Report modal when the header action is clicked", () => {
    render(<CM />);

    fireEvent.click(screen.getByRole("button", { name: "+ Create CM Report" }));

    expect(screen.getByRole("heading", { name: "Create CM Report" })).toBeTruthy();
  });

  it("creates a new CM report via the modal, closes it, and selects the new entry", () => {
    render(<CM />);

    fireEvent.click(screen.getByRole("button", { name: "+ Create CM Report" }));
    fireEvent.change(screen.getByLabelText("Equipment"), { target: { value: "533-P-1" } });
    fireEvent.change(screen.getByLabelText("Failure Description"), {
      target: { value: "Discharge pressure gauge reading erratic." },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create CM Report" }));

    expect(
      screen.queryByRole("heading", { name: "Create CM Report" })
    ).toBeNull();
    expect(
      screen.getByRole("heading", { name: "Discharge pressure gauge reading erratic." })
    ).toBeTruthy();
    expect(screen.getByText("CM-3009")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("CM-3009 created.");
  });
});

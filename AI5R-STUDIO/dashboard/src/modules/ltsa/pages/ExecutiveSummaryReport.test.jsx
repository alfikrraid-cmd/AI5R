import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ExecutiveSummaryReport from "./ExecutiveSummaryReport";

describe("Executive Summary Report", () => {
  it("renders the report header and print button", () => {
    render(<ExecutiveSummaryReport />);

    expect(screen.getByRole("heading", { name: "Executive Summary Report" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Print / Save as PDF" })).toBeTruthy();
  });

  it("reuses the Executive Dashboard sections with live derived data", () => {
    render(<ExecutiveSummaryReport />);

    expect(screen.getByRole("heading", { name: "Open Work Orders" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Maintenance Health" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Assets Requiring Attention" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Upcoming Maintenance" })).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
  });
});

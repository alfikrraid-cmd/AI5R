import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ExecutiveDashboard from "./ExecutiveDashboard";

describe("Executive Dashboard page", () => {
  it("renders the page header", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);

    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeTruthy();
  });

  it("renders the Executive KPI Cards first, ahead of Quick Navigation", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);

    const headings = screen.getAllByRole("heading").map((heading) => heading.textContent);
    const kpiIndex = headings.indexOf("Open Work Orders");
    const navigationIndex = headings.indexOf("Quick Navigation");

    expect(kpiIndex).toBeGreaterThan(-1);
    expect(navigationIndex).toBeGreaterThan(-1);
    expect(kpiIndex).toBeLessThan(navigationIndex);
  });

  it("renders Maintenance Health, Assets Requiring Attention, Upcoming Maintenance, and Recent Activities", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);

    expect(screen.getByRole("heading", { name: "Maintenance Health" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Assets Requiring Attention" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Upcoming Maintenance" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Recent Activities" })).toBeTruthy();
  });

  it("renders at least one attention asset derived from sample data", () => {
    render(<ExecutiveDashboard onNavigate={() => {}} />);

    expect(screen.getByText("641-P-5")).toBeTruthy();
  });

  it("calls onNavigate with the correct workspace key from Quick Navigation", () => {
    const onNavigate = vi.fn();
    render(<ExecutiveDashboard onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole("button", { name: "Open Asset 360" }));

    expect(onNavigate).toHaveBeenCalledWith("history");
  });
});

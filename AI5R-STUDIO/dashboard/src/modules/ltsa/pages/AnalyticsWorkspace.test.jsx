import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AnalyticsWorkspace from "./AnalyticsWorkspace";

describe("Analytics workspace page", () => {
  it("renders the page header", () => {
    render(<AnalyticsWorkspace />);

    expect(screen.getByRole("heading", { level: 1, name: "Analytics" })).toBeTruthy();
  });

  it("answers the four Product Owner questions in priority order", () => {
    const { container } = render(<AnalyticsWorkspace />);

    expect(screen.getByRole("heading", { name: "Are we healthy?" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "What needs attention?" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "What is getting worse?" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "What should managers do next?" })).toBeTruthy();

    const text = container.textContent;
    const positions = [
      "Are we healthy?",
      "What needs attention?",
      "What is getting worse?",
      "What should managers do next?",
    ].map((question) => text.indexOf(question));

    expect(positions).toEqual([...positions].sort((a, b) => a - b));
  });

  it("renders Maintenance KPIs and Maintenance Health under 'Are we healthy?'", () => {
    render(<AnalyticsWorkspace />);

    expect(screen.getByRole("heading", { name: "Open Work Orders" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Maintenance Health" })).toBeTruthy();
  });

  it("renders Asset Criticality Distribution and attention assets under 'What needs attention?'", () => {
    render(<AnalyticsWorkspace />);

    expect(screen.getByRole("heading", { name: "Asset Criticality Distribution" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Assets Requiring Attention" })).toBeTruthy();
    expect(screen.getByText("641-P-5")).toBeTruthy();
  });

  it("renders the Maintenance Activity Trend under 'What is getting worse?'", () => {
    render(<AnalyticsWorkspace />);

    expect(screen.getByRole("heading", { name: "Maintenance Activity Trend" })).toBeTruthy();
    expect(screen.getByText("This Week")).toBeTruthy();
  });

  it("renders Recommended Actions under 'What should managers do next?'", () => {
    render(<AnalyticsWorkspace />);

    expect(screen.getByRole("heading", { name: "Recommended Actions" })).toBeTruthy();
  });
});

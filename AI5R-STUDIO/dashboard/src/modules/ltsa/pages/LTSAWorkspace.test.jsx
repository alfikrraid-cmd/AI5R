import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import LTSAWorkspace from "./LTSAWorkspace";

afterEach(() => {
  window.history.pushState({}, "", "/");
});

describe("LTSAWorkspace navigation shell", () => {
  it("renders a tab for every LTSA workspace", () => {
    render(<LTSAWorkspace />);

    expect(screen.getByRole("tab", { name: "Executive Dashboard" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Pump" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Work Order" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Preventive Maintenance" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Corrective Maintenance" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Asset 360" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Reports" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Analytics" })).toBeTruthy();
  });

  it("defaults to the Executive Dashboard", () => {
    render(<LTSAWorkspace />);

    expect(screen.getByRole("tab", { name: "Executive Dashboard" }).getAttribute("aria-selected")).toBe(
      "true"
    );
    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeTruthy();
  });

  it("switches to the Pump workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Pump" }));

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Executive Dashboard" })).toBeNull();
  });

  it("switches to the Work Order workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Work Order" }));

    expect(screen.getByRole("heading", { name: "Work Order Workspace" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Executive Dashboard" })).toBeNull();
  });

  it("switches to the Preventive Maintenance workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Preventive Maintenance" }));

    expect(screen.getByRole("heading", { name: "Preventive Maintenance Workspace" })).toBeTruthy();
  });

  it("switches to the Corrective Maintenance workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Corrective Maintenance" }));

    expect(screen.getByRole("heading", { name: "Corrective Maintenance Workspace" })).toBeTruthy();
  });

  it("switches to the Asset 360 workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Asset 360" }));

    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();
  });

  it("switches to the Reports workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Reports" }));

    expect(screen.getByRole("heading", { name: "Executive Summary Report" })).toBeTruthy();
  });

  it("switches to the Analytics workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Analytics" }));

    expect(screen.getByRole("heading", { level: 1, name: "Analytics" })).toBeTruthy();
  });

  it("completes a first-time-user demo walkthrough across every workspace without error", () => {
    render(<LTSAWorkspace />);

    // Land on the Executive Dashboard by default.
    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeTruthy();

    // Jump to Pump Registry via Quick Navigation, select a pump, view its detail.
    fireEvent.click(screen.getByRole("button", { name: "Open Pump Registry" }));
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();

    fireEvent.click(screen.getByText("305-P-2"));
    expect(screen.getByRole("heading", { name: "Cooling Water Circulation Pump" })).toBeTruthy();

    // Follow the pump's "View History" quick action into Maintenance History.
    fireEvent.click(screen.getByRole("button", { name: "View History" }));
    expect(screen.getByRole("heading", { name: "Pump Workspace" })).toBeTruthy();

    // Return to the Dashboard and jump to Reports via Quick Navigation.
    fireEvent.click(screen.getByRole("tab", { name: "Executive Dashboard" }));
    fireEvent.click(screen.getByRole("button", { name: "Open Reports" }));
    expect(screen.getByRole("heading", { name: "Executive Summary Report" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Print / Save as PDF" })).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Pump History Report" }));
    expect(screen.getByRole("heading", { name: "Pump History Report" })).toBeTruthy();

    // Return to the Dashboard and jump to Analytics via Quick Navigation.
    fireEvent.click(screen.getByRole("tab", { name: "Executive Dashboard" }));
    fireEvent.click(screen.getByRole("button", { name: "Open Analytics" }));
    expect(screen.getByRole("heading", { level: 1, name: "Analytics" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Are we healthy?" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "What should managers do next?" })).toBeTruthy();

    // Every outer LTSA tab remains reachable after this journey.
    ["Executive Dashboard", "Pump", "Work Order", "Preventive Maintenance", "Corrective Maintenance", "Asset 360", "Reports", "Analytics"].forEach(
      (tabName) => {
        expect(screen.getByRole("tab", { name: tabName })).toBeTruthy();
      }
    );
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LTSAWorkspace from "./LTSAWorkspace";

describe("LTSAWorkspace navigation shell", () => {
  it("renders a tab for every LTSA workspace", () => {
    render(<LTSAWorkspace />);

    expect(screen.getByRole("tab", { name: "Executive Dashboard" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Pump" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Work Order" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Preventive Maintenance" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Corrective Maintenance" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Maintenance History" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Reports" })).toBeTruthy();
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

  it("switches to the Maintenance History workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Maintenance History" }));

    expect(screen.getByRole("heading", { name: "Maintenance History" })).toBeTruthy();
  });

  it("switches to the Reports workspace when its tab is clicked", () => {
    render(<LTSAWorkspace />);

    fireEvent.click(screen.getByRole("tab", { name: "Reports" }));

    expect(screen.getByRole("heading", { name: "Executive Summary Report" })).toBeTruthy();
  });
});

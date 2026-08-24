import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import QuickNavigationPanel from "./QuickNavigationPanel";

describe("QuickNavigationPanel", () => {
  it("renders every quick navigation action", () => {
    render(<QuickNavigationPanel onNavigate={() => {}} />);

    // MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- retitled "Quick Actions"
    expect(screen.getByRole("heading", { name: "Quick Actions" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Pump Registry" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Work Orders" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Preventive Maintenance" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Corrective Maintenance" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Asset 360" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Reports" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Analytics" })).toBeTruthy();
  });

  it("calls onNavigate with the correct workspace key for each action", () => {
    const onNavigate = vi.fn();
    render(<QuickNavigationPanel onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole("button", { name: "Open Pump Registry" }));
    expect(onNavigate).toHaveBeenCalledWith("pump");

    fireEvent.click(screen.getByRole("button", { name: "Open Work Orders" }));
    expect(onNavigate).toHaveBeenCalledWith("workorder");

    fireEvent.click(screen.getByRole("button", { name: "Open Preventive Maintenance" }));
    expect(onNavigate).toHaveBeenCalledWith("pm");

    fireEvent.click(screen.getByRole("button", { name: "Open Corrective Maintenance" }));
    expect(onNavigate).toHaveBeenCalledWith("cm");

    fireEvent.click(screen.getByRole("button", { name: "Open Asset 360" }));
    expect(onNavigate).toHaveBeenCalledWith("history");

    fireEvent.click(screen.getByRole("button", { name: "Open Reports" }));
    expect(onNavigate).toHaveBeenCalledWith("reports");

    fireEvent.click(screen.getByRole("button", { name: "Open Analytics" }));
    expect(onNavigate).toHaveBeenCalledWith("analytics");
  });
});
